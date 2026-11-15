"""Import thousands of official CC0 Lichess puzzles in manageable 100-row batches."""
import argparse,csv,json,urllib.parse,urllib.request
from db import DB,Puzzle,initialize
from content import from_lichess
def run(limit=2000,offset=0,batches=200):
    initialize();count=0
    for n in range(batches):
        q=urllib.parse.urlencode(dict(dataset="Lichess/chess-puzzles",config="default",split="train",offset=offset+n*100,length=100))
        request=urllib.request.Request("https://datasets-server.huggingface.co/rows?"+q,headers={"User-Agent":"JChess/1.0"})
        try:
            with urllib.request.urlopen(request,timeout=30) as r:batch=json.load(r).get("rows",[])
        except Exception as ex:
            print("Stopped after",count,"puzzles:",ex);break
        if not batch:break
        with DB.begin() as db:
            for entry in batch:
                d=entry.get("row") or {}
                rating=int(d.get("Rating",0));pop=int(d.get("Popularity",0))
                if not (550<=rating<=1500 and pop>=65):continue
                if isinstance(d.get("Themes"),list):d["Themes"]=" ".join(d["Themes"])
                if isinstance(d.get("Moves"),list):d["Moves"]=" ".join(d["Moves"])
                if "veryLong" in d.get("Themes",""):continue
                p=from_lichess(d)
                if not p or db.get(Puzzle,p["id"]):continue
                p["solution"]=json.dumps(p["solution"])
                db.add(Puzzle(**p));count+=1
                if count>=limit:break
        print("Imported",count,"puzzles",flush=True)
        if count>=limit:break
    return count
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--limit",type=int,default=2000)
    parser.add_argument("--offset",type=int,default=0)
    parser.add_argument("--batches",type=int,default=200)
    a=parser.parse_args();run(a.limit,a.offset,a.batches)
