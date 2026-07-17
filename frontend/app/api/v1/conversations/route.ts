import { requireAuth } from "@/lib/mock/http";
import { store } from "@/lib/mock/store";

// ConversationListCreateAPIView (명세 19장)
export async function GET(request: Request) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  const conversations = store.conversations.filter((conversation) =>
    conversation.participants.some((participant) => participant.id === user.id)
  );

  return Response.json(conversations);
}
