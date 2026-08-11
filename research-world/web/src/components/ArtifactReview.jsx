import { Check, PencilLine, RotateCcw, X } from "lucide-react";
import { useState } from "react";
import { useWorld } from "../context/WorldContext";
import { FeedbackDialog } from "./FeedbackDialog";

const REVIEWABLE = new Set(["pending", "pending_review", "submitted"]);

export function ArtifactReview({ artifact }) {
  const { command } = useWorld();
  const [busy, setBusy] = useState("");
  const [action, setAction] = useState("");
  if (!REVIEWABLE.has(artifact.status)) return null;
  const review = async (decision, feedback = "") => {
    setBusy(decision);
    try { await command("review_artifact", { artifact_id: artifact.id, decision, feedback }); setAction(""); }
    catch {}
    finally { setBusy(""); }
  };
  return <><div className="review-actions"><button className="button approve" disabled={busy} onClick={() => review("approve")}><Check size={16} />通过</button><button className="button secondary" disabled={busy} onClick={() => setAction("revise")}><PencilLine size={16} />要求修改</button><button className="button secondary" disabled={busy} onClick={() => setAction("restart")}><RotateCcw size={16} />重新执行</button><button className="button danger" disabled={busy} onClick={() => setAction("reject")}><X size={16} />拒绝</button></div><FeedbackDialog key={action} action={action} noun="产物" busy={Boolean(busy)} onClose={() => setAction("")} onSubmit={(feedback) => review(action, feedback)} /></>;
}
