"""Deduplicated advisory events. Never publish assistant events into policies."""
import time


class Events:
    def __init__(self, store):
        self.store,self.last,self.queue = store,{},[]

    def emit(self, key, text, priority=2, cooldown=30):
        if time.time()-self.last.get(key,0)<cooldown:
            return
        self.last[key] = time.time()
        event = {"id":str(time.time_ns()),"key":key,"text":text,"priority":priority,
                 "time":time.time(),"acknowledged":False,"audience":"operator"}
        self.queue = sorted((self.queue+[event])[-30:],key=lambda e:(e["priority"],-e["time"]))
        self.store.audit("advisory_event",event)

    def acknowledge(self, identifier):
        for event in self.queue:
            if event["id"]==identifier:
                event["acknowledged"] = True

    def pending(self):
        return [e for e in self.queue if not e["acknowledged"]]
