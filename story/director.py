"""Compile the writer's physical stage directions into verified rig controls.
No generated code is evaluated. Quiet acting remains possible; unsupported detail is reported.
"""
from __future__ import annotations
import copy
import re

# Ordered concrete actions, never inferred from a psychological diagnosis.
RULES = [
 (r"\b(?:stands? up|rises? from (?:the |a )?(?:chair|seat|bench))\b", "standup"),
 (r"\b(?:sits? down|lowers? .*? (?:chair|seat))\b", "sitdown"),
 (r"\b(?:draws?|drawing|sketches|sketching|traces?|writes?|writing)\b", "write"),
 (r"\b(?:shows?|reveals?|holds? out)\b.{0,50}\b(?:sketch|book|drawing|page)\b", "show"),
 (r"\b(?:reads?|reading|opens? (?:a |the )?book)\b", "read"),
 (r"\b(?:runs?|running|sprints?)\b", "run"),
 (r"\b(?:walks?|walking|steps? (?:forward|away|toward)|approaches?|enters?)\b", "walk"),
 (r"\b(?:types?|typing)\b", "type"),
 (r"\b(?:checks?|checking|scrolls?|scrolling)\b.{0,30}\bphone\b", "phone"),
 (r"\b(?:waves?|waving)\b", "wave"),
 (r"\b(?:shrugs?|shrugging)\b", "shrug"),
 (r"\b(?:points?|pointing)\b", "point"),
 (r"\b(?:laughs?|laughing)\b", "laugh"),
 (r"\b(?:cries|crying|weeps?)\b", "cry"),
 (r"\b(?:thinks?|thinking|ponders?|considers?|wonders?)\b", "think"),
 (r"\b(?:asks?|answers?|explains?|speaks?|says|replies|gestures?|talks?)\b", "talk"),
];
IDLE = {"stand", "sit", "pockets"}

def physical_actions(beat):
    text = str(beat.get("what_happens") or "")
    # Keep sentence order; the engine implements each motion.
    found=[]
    for clause in re.split(r"[.;]|\bthen\b",text,flags=re.I):
        if re.match(r"^\s*(?:the|a|his|her)\s+(?:drawing|writing)\s+(?:is|was|represents)",clause,re.I): continue
        for pattern, pose in RULES:
            if re.search(pattern,clause,re.I):
                found.append((pose,clause.strip())); break
    return found

def apply_performance(shot, beat, phase=0, force=False):
    """Preserve narration, duration and voice paths when redirection is requested."""
    actions=physical_actions(beat)
    changes=[]
    actors=shot.get("actors") or []
    people=[a for a in actors if a.get("id")!="demon"]
    for i,a in enumerate(people):
        semantic=" ".join([str(beat.get("what_happens") or ""),*[(n.get("text","") if isinstance(n,dict) else str(n)) for n in beat.get("narration") or []]])
        phone_context=bool(re.search(r"\b(?:phone|text|message|reply|chat)\b",semantic,re.I)) and not re.search(r"\b(?:laptop|computer|keyboard)\b",semantic,re.I)
        if a.get("pose") in {"type","read","write"} and phone_context:
            if a["pose"] in {"type","write"}:a["seated"]=True
            a["pose"]="phone";a["hold"]="phone"
        if not force and a.get("pose","stand") not in IDLE: continue
        actor_id=str(a.get("id",""))
        def subject(clause):
            match=re.match(r"^\s*([A-Za-z_]+)\b",clause)
            name=match.group(1).lower() if match else ""
            return next((str(p.get("id")) for p in people if str(p.get("id")).lower()==name),None)
        own=[item for item in actions if subject(item[1])==actor_id]
        unnamed=[item for item in actions if subject(item[1]) is None]
        # A recipient is not the actor: "Alex shows Sam" must not make Sam show a book.
        relevant=own or (unnamed if i==0 else [])
        if relevant:
            pose,clause=relevant[min(phase,len(relevant)-1)]
        elif any(l.get("who")==actor_id for l in shot.get("lines") or []):
            pose,clause="talk","character dialogue"
        else:
            continue
        if pose in {"type","read","write"} and phone_context:pose="phone"
        old=a.get("pose","stand")
        seated=old in {"sit","slump","type","write"} or a.get("seated") is True
        a["pose"]=pose
        if seated and pose not in {"walk","run"}: a["seated"]=True
        if pose in {"walk","run"}:
            a.pop("seated",None)
            start=float(a.get("x",50))
            # Grounded traversal at a restrained speed; no instant entrance.
            delta=min(25,max(8,float(shot.get("dur",4))*3))
            direction=-1 if re.search(r"\b(?:away|left)\b",clause,re.I) else 1
            a["to"]=max(8,min(92,start+direction*delta))
            a["facing"]=direction
        if pose=="phone":a["hold"]="phone"
        if pose in {"write","read","show"}:
            a["hold"]="pencil" if pose=="write" else "book"
            if re.search(r"\b(?:seedling|sprout|plant)\b",str(beat),re.I): a["artwork"]="seedling"
        if len(people)>1:
            other=people[1-i] if i<2 else people[0]
            a["target"]=other["id"]
            a["facing"]=1 if float(other.get("x",50))>float(a.get("x",50)) else -1
        changes.append({"actor":actor_id,"from":old,"to":pose,"direction":clause})
    return changes

def resolve_blocking(shot,clearance=10):
    """Stop approaches beside a partner instead of through their body."""
    changes=[]
    for actor in shot.get("actors",[]):
        if actor.get("pose") not in {"walk","run"} or "to" not in actor:continue
        start=float(actor.get("x",50));goal=float(actor["to"]);direction=1 if goal>=start else -1
        candidates=[float(other.get("x",50)) for other in shot["actors"] if other is not actor and other.get("depth")==actor.get("depth")]
        for obstacle in sorted(candidates,reverse=direction<0):
            if direction>0 and start<obstacle and goal>obstacle-clearance:goal=max(start,obstacle-clearance)
            if direction<0 and start>obstacle and goal<obstacle+clearance:goal=min(start,obstacle+clearance)
        if goal!=actor["to"]:
            changes.append({"actor":actor["id"],"requested":actor["to"],"resolved":goal})
            actor["to"]=goal
    return changes

def direct_beat(beat,vocab):
    from story.staging import compile_staging
    explicit=compile_staging(beat)
    if explicit is not None:
        for shot in explicit:shot["blocking_changes"]=resolve_blocking(shot)
        return explicit
    mood=beat.get("emotion") if beat.get("emotion") in vocab["moods"] else "neutral"
    where=beat.get("where","void")
    seated=bool(vocab["sets"].get(where,{}).get("seat"))
    who=[w for w in beat.get("who",[]) if isinstance(w,str) and w!="demon"][:3] or ["hero"]
    base={k:copy.deepcopy(beat[k]) for k in ("time","weather","grade","scene") if beat.get(k)}
    base["set"]=where
    actions=physical_actions(beat)
    count=max(2,min(4,len(actions)))
    shots=[]
    for phase in range(count):
        actors=[{"id":pid,"x":38+i*24 if len(who)>1 else 50,"pose":"sit" if seated else "stand","mood":mood,
                 "facing":1 if i==0 else -1} for i,pid in enumerate(who)]
        shot={**copy.deepcopy(base),"dur":max(3,float(beat.get("seconds",10))/count),
              "camera":{"frame":"two" if len(who)>1 else ("wide" if phase==0 else "medium"),"on":who[0],"push":.025},
              "actors":actors,"lines":[]}
        if phase==0: shot["lines"]=copy.deepcopy(beat.get("dialogue") or [])
        if shots:
            prior={a["id"]:a for a in shots[-1]["actors"]}
            for actor in actors:
                before=prior.get(actor["id"],{})
                actor["x"]=before.get("to",before.get("x",actor["x"]))
        shot["acting_changes"]=apply_performance(shot,beat,phase)
        shot["blocking_changes"]=resolve_blocking(shot)
        shots.append(shot)
    return shots

def enrich_film(film,sheet):
    report=[]
    phases={};artwork={}
    for i,shot in enumerate(film["shots"]):
        index=int(shot.get("beat",0))-1
        if index<0 or index>=len(sheet.get("beats",[])) or shot.get("card"):continue
        phase=phases.get(index,0); phases[index]=phase+1
        changed=[] if shot.get('_directed') else apply_performance(shot,sheet["beats"][index],phase)
        for actor in shot.get("actors",[]):
            if actor.get("artwork"):artwork[actor["id"]]=actor["artwork"]
            elif actor.get("pose") in ("read","show") and actor["id"] in artwork:actor["artwork"]=artwork[actor["id"]]
        blocking=resolve_blocking(shot)
        if blocking:shot["blocking_changes"]=blocking
        if changed: report.append({"shot":i,"beat":index+1,"changes":changed})
    film["acting_report"]={"director":"verified physical-action compiler","changes":report,
      "limitations":["Unsupported physical detail is not simulated; inspect scene meaning in the contact sheet.",
                    "Thoughtful standing and sitting are permitted, not counted as new performances."]}
    return film
