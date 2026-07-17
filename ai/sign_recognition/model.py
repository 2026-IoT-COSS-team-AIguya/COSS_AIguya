"""수어 keypoint 시퀀스 -> 임베딩 벡터를 만드는 인코더 + 메트릭 러닝 손실함수.

분류기(softmax)가 아니라 "같은 단어면 벡터가 가깝게, 다른 단어면 멀게" 학습하는
구조라서(Supervised Contrastive Loss), 클래스당 예시가 몇 개 안 돼도 학습이 되고
나중에 새 단어를 추가할 때도 재학습 없이 등록(enroll)만 하면 된다.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import VideoMAEModel

from keypoints import FEATURE_DIM  # 225


def _branch(in_ch: int, hidden: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv1d(in_ch, hidden, kernel_size=5, padding=2),
        nn.BatchNorm1d(hidden),
        nn.ReLU(inplace=True),
        nn.Conv1d(hidden, hidden, kernel_size=5, padding=2, stride=2),
        nn.BatchNorm1d(hidden),
        nn.ReLU(inplace=True),
    )


class SignEncoder(nn.Module):
    """[B, T, 225] keypoint 시퀀스 -> [B, embed_dim] L2-정규화된 임베딩.

    pose(33)/왼손(21)/오른손(21)을 하나로 뭉쳐서 넣지 않고 부위별로 따로
    conv branch를 태운 뒤 합친다 -- "이건 손모양 특징, 이건 팔 위치 특징"처럼
    구조를 명시적으로 알려주면 이 정도 데이터量에서도 더 잘 배운다.

    시간축에 1D CNN을 쓰고 마지막에 global average pooling을 하기 때문에
    입력 프레임 길이(T)가 달라도 그대로 처리된다.
    """

    N_POSE = 33
    N_HAND = 21

    def __init__(self, in_dim: int = FEATURE_DIM, embed_dim: int = 192, hidden: int = 128, dropout: float = 0.3):
        super().__init__()
        assert in_dim == (self.N_POSE + self.N_HAND * 2) * 3

        self.pose_branch = _branch(self.N_POSE * 3, hidden)
        self.lhand_branch = _branch(self.N_HAND * 3, hidden)
        self.rhand_branch = _branch(self.N_HAND * 3, hidden)

        fused_ch = hidden * 3
        self.fuse = nn.Sequential(
            nn.Conv1d(fused_ch, fused_ch, kernel_size=3, padding=1),
            nn.BatchNorm1d(fused_ch),
            nn.ReLU(inplace=True),
            nn.Conv1d(fused_ch, fused_ch, kernel_size=3, padding=1, stride=2),
            nn.BatchNorm1d(fused_ch),
            nn.ReLU(inplace=True),
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(fused_ch, fused_ch),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(fused_ch, embed_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, T, 225] -> conv1d는 [B, C, T]를 기대하므로 transpose
        x = x.transpose(1, 2)  # [B, 225, T]
        pose = x[:, : self.N_POSE * 3, :]
        lhand = x[:, self.N_POSE * 3 : self.N_POSE * 3 + self.N_HAND * 3, :]
        rhand = x[:, self.N_POSE * 3 + self.N_HAND * 3 :, :]

        pose_feat = self.pose_branch(pose)
        lhand_feat = self.lhand_branch(lhand)
        rhand_feat = self.rhand_branch(rhand)

        fused = torch.cat([pose_feat, lhand_feat, rhand_feat], dim=1)
        fused = self.fuse(fused)
        pooled = self.pool(fused).squeeze(-1)
        out = self.head(pooled)
        return F.normalize(out, dim=-1)


def supervised_contrastive_loss(
    embeddings: torch.Tensor, labels: torch.Tensor, temperature: float = 0.1
) -> torch.Tensor:
    """SupCon loss (Khosla et al. 2020)의 단순화 버전.

    같은 라벨(같은 단어)끼리는 임베딩이 가깝게, 다른 라벨끼리는 멀게 만든다.
    배치 안에 각 단어별로 여러 증강 샘플이 섞여 들어온다는 전제.
    """
    device = embeddings.device
    n = embeddings.shape[0]
    sim = embeddings @ embeddings.T / temperature  # [N, N] 코사인 유사도(정규화되어 있으니 내적=코사인)

    # 자기 자신 제외
    self_mask = torch.eye(n, dtype=torch.bool, device=device)
    sim = sim.masked_fill(self_mask, float("-inf"))

    labels = labels.view(-1, 1)
    positive_mask = (labels == labels.T) & ~self_mask  # 같은 라벨 = positive

    # 양성 샘플이 하나도 없는 행(배치에 그 단어가 1개뿐)은 loss 계산에서 제외
    has_positive = positive_mask.any(dim=1)

    log_prob = sim - torch.logsumexp(sim, dim=1, keepdim=True)
    # 주의: positive_mask * log_prob 로 쓰면 안 됨 -- log_prob의 대각선(자기 자신)은
    # -inf인데 0(False) * -inf = NaN 이 되어(IEEE754) 전체가 오염된다. torch.where로
    # -inf 위치를 아예 0으로 치환한 뒤 골라내야 안전하다.
    safe_log_prob = torch.where(positive_mask, log_prob, torch.zeros_like(log_prob))
    mean_log_prob_pos = safe_log_prob.sum(dim=1) / positive_mask.sum(dim=1).clamp(min=1)

    loss = -mean_log_prob_pos[has_positive]
    if loss.numel() == 0:
        return torch.tensor(0.0, device=device, requires_grad=True)
    return loss.mean()


class VideoMAEEncoder(nn.Module):
    """Kinetics-400으로 사전학습된 VideoMAE(8600만 파라미터)를 백본으로 쓰는 인코더.

    [B, 16, 3, 224, 224] 영상 프레임 텐서 -> [B, embed_dim] L2-정규화 임베딩.

    데이터가 84개뿐이라 backbone을 통째로 파인튜닝하면 바로 망가진다. 그래서
    - 트랜스포머 12개 층 중 마지막 n_unfrozen개만 학습(unfreeze)하고
    - 나머지는 얼려서(freeze) 사전학습 지식을 그대로 보존한다.
    """

    def __init__(self, embed_dim: int = 128, n_unfrozen: int = 2, dropout: float = 0.3):
        super().__init__()
        self.backbone = VideoMAEModel.from_pretrained("MCG-NJU/videomae-base")
        hidden = self.backbone.config.hidden_size  # 768

        for p in self.backbone.parameters():
            p.requires_grad = False
        n_layers = len(self.backbone.encoder.layer)
        for layer in self.backbone.encoder.layer[n_layers - n_unfrozen :]:
            for p in layer.parameters():
                p.requires_grad = True

        # 시퀀스 길이가 1568토큰이라 어텐션 행렬(batch x heads x 1568 x 1568)이
        # 역전파용으로 저장되면 배치 84 기준 8GB VRAM을 훌쩍 넘긴다. gradient
        # checkpointing으로 순전파 결과를 저장하지 않고 역전파 때 다시 계산해서
        # 메모리 대신 연산량을 쓰도록 바꾼다.
        self.backbone.gradient_checkpointing_enable()

        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden, hidden // 2),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden // 2, embed_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, 16, 3, 224, 224]
        out = self.backbone(x).last_hidden_state  # [B, num_patches, hidden]
        pooled = out.mean(dim=1)  # 패치 전체 평균 풀링
        emb = self.head(pooled)
        return F.normalize(emb, dim=-1)

    def trainable_parameters(self):
        return [p for p in self.parameters() if p.requires_grad]
