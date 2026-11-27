"""Assistant-only session state. Native records retain outcome authority."""
PHASES = ("preflight","setup","demonstrate","reveal","verify_saved","reset")


class Workflow:
    def __init__(self, store):
        self.store = store

    def current(self, session):
        return self.store.state("workflow:"+session,{"phase":"preflight","step":0,"paused":False})

    def instruction(self, session, card):
        state = self.current(session)
        if state["paused"]:
            return "The guided session is paused. Say resume when you are ready."
        phase = state["phase"]
        steps = card.get(phase,[]) if phase not in ("verify_saved",) else []
        instruction = steps[min(state["step"],len(steps)-1)] if steps else "Check the native saved episode and its admission receipt before continuing."
        return {"state":state,"instruction":instruction,"authority":"Project recording card; operator confirmations do not prove native admission"}

    def action(self, session, action, card):
        state = self.current(session)
        if action in ("pause","resume"):
            state["paused"] = action=="pause"
        elif action == "next" and not state["paused"]:
            steps = card.get(state["phase"],[])
            if state["step"]+1<len(steps):
                state["step"] += 1
            else:
                index = min(PHASES.index(state["phase"])+1,len(PHASES)-1)
                state.update(phase=PHASES[index],step=0)
        elif action == "restart":
            state = {"phase":"preflight","step":0,"paused":False}
        self.store.put("workflow:"+session,state)
        self.store.audit("workflow",{"session":session,"action":action,"state":state})
        return self.instruction(session,card)
