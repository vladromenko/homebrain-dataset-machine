"""Live HTTP requests; outcomes are audited separately from physical verification."""
import json
from pathlib import Path
import time
import httpx
from homebrain.config import ROOT

PROMPTS = ["What should I record next?","Show me the laboratory camera.",
           "Can you see the gripper and both containers?","Has the camera moved?",
           "Is the new camera position suitable?","Which dataset should I select?",
           "Has my last demonstration been saved?","Why was this episode rejected?",
           "How many accepted demonstrations do I have?","Why did ACT fail to grasp the object?",
           "What evidence is still missing for my paper?","Explain this function in the project.",
           "Switch to the Explorer project.","Repeat the previous instruction."]


def run():
    token = (ROOT/"runtime/access-token").read_text().strip()
    rows,project = [],"smart-swarm"
    with httpx.Client(base_url="http://127.0.0.1:8090",headers={"Authorization":"Bearer "+token},timeout=180,trust_env=False) as client:
        for prompt in PROMPTS:
            started,text,sources = time.monotonic(),"",[]
            with client.stream("POST","/api/chat",json={"text":prompt,"session":"acceptance-20261127","project":project}) as response:
                code = response.status_code
                for line in response.iter_lines():
                    if line:
                        event = json.loads(line)
                        text += event.get("text") or event.get("token") or ""
                        sources += event.get("sources",[])
                        project = event.get("project",project)
            row = {"request":prompt,"http_status":code,"elapsed_s":time.monotonic()-started,"response":text,"sources":sources,"project":project,"review":"pending_semantic_review","physical_success_claimed":False}
            rows.append(row)
            (ROOT/"evaluation/acceptance-live.json").write_text(json.dumps(rows,indent=2))
            print(prompt,code,round(row["elapsed_s"],2),flush=True)


if __name__=="__main__":
    run()
