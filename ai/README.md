\# AI Development Environment



이 폴더는 COSS\_AIguya 프로젝트의 AI 기능 개발을 위한 공간입니다.



\## 주요 기능



1\. 수어 영상에서 키워드 추출

2\. 추출된 키워드를 자연어 문장으로 변환

3\. 텍스트에서 키워드 추출

4\. 키워드에 맞는 수어 영상 매칭



\## 가상환경



이 프로젝트에서는 `coss` conda 가상환경을 사용합니다.



```bash

conda activate coss

```



\## 패키지 설치



```bash

pip install -r ai/requirements-ai.txt

```



또는 conda 환경 파일을 사용할 경우:



```bash

conda env create -f ai/environment.yml

conda activate coss

```



\## GPU 확인



```bash

python ai/check\_gpu.py

```



정상적으로 설정되어 있다면 CUDA 사용 가능 여부와 GPU 이름이 출력됩니다.



\## 폴더 구조



```text

ai/

├─ README.md

├─ requirements-ai.txt

├─ environment.yml

├─ check\_gpu.py

├─ sign\_recognition/

├─ text\_to\_sign/

├─ sentence\_generation/

├─ pipeline/

├─ data/

├─ models/

└─ outputs/

```



\## 역할



\### sign\_recognition



수어 영상을 입력받아 핵심 키워드를 예측하는 모듈입니다.



\### text\_to\_sign



비장애인이 입력한 텍스트에서 키워드를 추출하고, 해당 키워드에 맞는 수어 영상을 찾는 모듈입니다.



\### sentence\_generation



수어 인식 모델이 추출한 키워드를 자연스러운 한국어 문장으로 변환하는 모듈입니다.



\### pipeline



수어 영상 → 키워드 → 문장, 텍스트 → 키워드 → 수어 영상 흐름을 연결하는 모듈입니다.



\## GitHub에 올리지 않는 파일



다음 파일들은 용량이 크거나 개인 환경에 의존하므로 GitHub에 올리지 않습니다.



\* AI Hub 원본 데이터셋

\* 수어 영상 원본 파일

\* 학습된 모델 파일

\* 추론 결과물

\* conda 가상환경 폴더

\* `.env` 파일



