"""Logical specializations share one inference server and remain sequential."""
INSTRUCTIONS = {
    "supervisor":"Coordinate the current operator task. Prefer one actionable step.",
    "perception":"Describe only observed images. No metric coordinates without calibrated fixed references.",
    "dataset":"Native manifests and admission receipts decide saved, accepted and rejected status. Preserve split ancestry.",
    "learning":"Separate decreasing loss from measured physical success. Diagnose from supplied configurations and evaluation evidence.",
    "hardware":"Report verified device identities, timestamps and native STOP evidence. Do not issue motor commands.",
    "software":"Explain approved source functions and interfaces using retrieved code. Commands are recommendations, never executed by you.",
    "research":"Separate hypotheses, baselines and demonstrated results. Cite supplied sources; never invent references or novelty.",
    "knowledge":"Compare source revision, hash, scope and indexing date. Explain conflicts and missing evidence."}


def route(text):
    query = text.lower()
    rules = [("perception",("camera","gripper visible","can you see")),
             ("dataset",("record","dataset","episode","demonstration")),
             ("learning",("act ","smolvla","training","checkpoint","optimizer")),
             ("hardware",("device","microphone","calibration","stop status")),
             ("software",("function","code","traceback","algorithm")),
             ("research",("paper","research","baseline","hypothesis","literature")),
             ("knowledge",("source","documentation","remember"))]
    return next((role for role,words in rules if any(word in query for word in words)),"supervisor")
