"""Source locations guide on-demand reads; excerpts never replace native receipts."""
import ast
from pathlib import Path


def locations(runtime, session):
    roots = getattr(runtime,'source_roots',{})
    root = roots.get('so101-studio' if session.get('robot_id')=='so101' else 'explorer')
    path = Path(root)/'src/so101_lab/recording.py' if root and session.get('robot_id')=='so101' else None
    if session.get('project_id')=='smart-swarm':
        peer = runtime.lab.swarm.registration()
        if peer:
            root = peer['repository_path']
            path = Path(root)/'src/smart_swarm/lab_domain.py'
    if path is None or not path.is_file():
        return []
    from ..adapters import approved
    path = approved(path,[root])
    text = path.read_text()
    definitions = [{'name':node.name,'start_line':node.lineno}
                   for node in ast.walk(ast.parse(text))
                   if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and 'validat' in node.name]
    quarantine = [index+1 for index,line in enumerate(text.splitlines())
                  if "quarantine" in line and ('warnings' in line or "status=='complete'" in line or "os.replace" in line)]
    reasons = [receipt.get('native_episode',{}).get('metadata',{}).get('reason','') for receipt in session.get('receipts',[])]
    if any(str(reason or '').startswith('operator_') for reason in reasons):
        definitions = []
        quarantine = list(reversed(quarantine))
    return [{'path':str(path),'validation_definitions':definitions[:8],
             'quarantine_lines':quarantine[:4], 'instruction':'Read relevant definitions with the source tool; historical receipt reasons remain authoritative.'}]
