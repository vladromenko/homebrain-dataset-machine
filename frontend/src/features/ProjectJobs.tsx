import { useEffect, useState } from 'react';
import { api, lab } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export function ProjectJobs() {
  const [evidence, setEvidence] = useState<any>(null);
  const [recipe, setRecipe] = useState<any>(null);
  const [message, setMessage] = useState('');
  useEffect(() => {
    const refresh = () => api(`${lab}/project-jobs`).then(setEvidence).catch(error => setMessage(String(error)));
    refresh(); const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, []);
  return <><div className="list-heading"><h2>Project-approved recipes</h2><span>Explicit submission · existing native reservations</span></div>
    {message && <p role="status">{message}</p>}
    <p className="muted">{evidence?.eligibility.reason || 'Checking the current project corpus…'}</p>
    <div className="task-list">{evidence?.recipes.map((item: any) => <Card className="task-row" key={item.id}>
      <div><h3>{item.model || item.purpose}</h3><p>{item.data}</p><p>{item.status.replaceAll('_', ' ')}</p></div>
      <Button variant="outline" disabled={!evidence.eligibility.eligible || !['native-act-fit-v1','native-smolvla-fit-v1'].includes(item.id)}
        onClick={() => setRecipe(item)}>Review job</Button>
    </Card>)}</div>
    {evidence?.operations.map((operation: any) => <p className="job-receipt" key={operation.operation_id}>
      {operation.recipe_id} · <Badge variant="outline">{operation.status}</Badge> · {operation.result?.message}
    </p>)}
    <Dialog open={!!recipe} onOpenChange={value => {if (!value) setRecipe(null);}}>
      <DialogContent><DialogHeader><DialogTitle>Review {recipe?.model} job</DialogTitle></DialogHeader>
        {recipe && <JobReview recipe={recipe} evidence={evidence} onResult={(text: string) => {setMessage(text); setRecipe(null);}}/>}
      </DialogContent>
    </Dialog>
  </>;
}

function JobReview({recipe, evidence, onResult}: any) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [review, setReview] = useState<any>(null);
  useEffect(() => {
    api(`${lab}/project-jobs/review`, {recipe_id: recipe.id, corpus_sha256: evidence.corpus_sha256, idempotency_key: crypto.randomUUID()})
      .then(result => {setReview(result.review); window.dispatchEvent(new CustomEvent('homebrain-selected-session', {detail: result.session}));})
      .catch(failure => setError(String(failure)));
  }, []);
  async function submit() {
    if (busy) return;
    setBusy(true);
    try {
      const result = await api(`${lab}/project-jobs`, {recipe_id: recipe.id, corpus_sha256: evidence.corpus_sha256, idempotency_key: review.idempotency_key});
      onResult(`${result.status}: ${result.message} (${result.operation_id})`);
    } catch (failure) {setError(String(failure)); setBusy(false);}
  }
  return <><p>{recipe.purpose}. Source: {recipe.source}.</p>
    <p>{evidence.eligibility.train_source_groups} train groups · {evidence.eligibility.validation_source_groups} separate validation groups.</p>
    <p>At most {recipe.updates_cap} updates / {Math.round(recipe.wall_seconds_cap / 60)} minutes. {recipe.compute_profile}.</p>
    <p>The project rechecks this reviewed corpus before starting. Raw recordings stay in their native store.</p>
    {error && <p role="alert">{error}</p>}
    <Button disabled={busy || !review} onClick={submit}>{busy ? 'Submitting reviewed job…' : 'Submit reviewed job'}</Button>
  </>;
}
