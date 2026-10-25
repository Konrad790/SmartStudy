import { BoardWorkspace } from "@/components/whiteboard/board-workspace";

type Props = { params: Promise<{ boardId: string }> };

export default async function BoardDetailPage({ params }: Props) {
  const { boardId } = await params;
  return <BoardWorkspace key={boardId} boardId={boardId} />;
}
