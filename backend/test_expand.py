import urllib.request
import json
import urllib.parse

def test():
    req = urllib.request.urlopen("http://localhost:8000/api/graph")
    data = json.loads(req.read())
    nodes = data.get("nodes", [])
    print(f"Initial graph has {len(nodes)} nodes.")
    
    expandable = []
    
    # Let's test expanding ALL nodes in the initial graph
    for n in nodes:
        node_id = n["id"]
        url = "http://localhost:8000/api/graph/expand/" + urllib.parse.quote(node_id)
        req2 = urllib.request.urlopen(url)
        data2 = json.loads(req2.read())
        
        # Check if there are any nodes in the response that aren't in the initial graph
        initial_ids = {x["id"] for x in nodes}
        new_ids = {x["id"] for x in data2.get("nodes", [])}
        
        added = new_ids - initial_ids
        if added:
            expandable.append((node_id, added))
            
    print(f"Found {len(expandable)} nodes that can be expanded to reveal new items.")
    for n, a in expandable[:5]:
        print(f"  - {n} reveals: {a}")

if __name__ == "__main__":
    test()
