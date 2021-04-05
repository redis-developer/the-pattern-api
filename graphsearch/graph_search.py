import redis
import config
from redisgraph import Graph

#TODO: move into config.py
import os 
config_switch=os.getenv('DOCKER', 'local')
if config_switch=='local':
    startup_nodes = [{"host": "127.0.0.1", "port": "30001"}, {"host": "127.0.0.1", "port":"30002"}, {"host":"127.0.0.1", "port":"30003"}]
    host="127.0.0.1"
    port=9001
else:
    startup_nodes = [{"host": "rgcluster", "port": "30001"}, {"host": "rgcluster", "port":"30002"}, {"host":"rgcluster", "port":"30003"}]
    host="redisgraph"
    port=6379

redis_client = redis.Redis(host=host,port=port,charset="utf-8", decode_responses=True)
redis_graph = Graph('cord19medical', redis_client)

from automata.utils import *

def match_nodes(search_string, Automata=Automata):
    if not Automata:
        Automata=loadAutomata()
    nodes=set()
    matched_ents=find_matches(search_string,Automata)
    nodes = set([node[0] for node in matched_ents])
    return list(nodes)



def get_nodes(nodes):
    # this will get list of nodes
    node_list=list()
    params = {'ids':nodes}
    query="""WITH $ids as ids MATCH (e:entity) where (e.id in ids) RETURN DISTINCT e.id,e.name,max(e.rank) LIMIT 400"""
    result = redis_graph.query(query, params)
    print(query)
    result.pretty_print()
    for record in result.result_set:
        node_list.append({'id':record[0],'name':record[1],'rank':record[2]})
    return node_list

def get_edges(nodes, years=None):
    """
    return all edges for the specified nodes, limit hardcoded
    """
    links=list()
    nodes_dict=dict()
    years_set=set()
    if years is not None:
        log("Graph query node params "+str(nodes))
        params = {'ids':nodes, 'years':years}
        query="""WITH $ids as ids MATCH (e:entity)-[r]->(t:entity) where (e.id in ids) and (r.year in $years) RETURN DISTINCT e.id, e.name,e.rank, t.id, t.name, t.rank, max(r.rank), r.year ORDER BY r.rank DESC"""
    else:
        params = {'ids':nodes}
        log("Graph query node params "+str(nodes))
        query="""WITH $ids as ids MATCH (e:entity)-[r]->(t:entity) where e.id in ids RETURN DISTINCT e.id, e.name,e.rank, t.id, t.name, t.rank, max(r.rank), r.year ORDER BY r.rank DESC"""

    result = redis_graph.query(query,params)
    result.pretty_print()
    for record in result.result_set:
        #FIXME: this is rather manual distinct on nodes, needs unique nodes in Aho-corasick matcher than this hack can be removed. 
        nodes_dict[record[1]]={"id":record[0],"rank":record[2]}
        nodes_dict[record[4]]={"id":record[3],"rank":record[5]}
        if record[7]:
            years_set.add(record[7])
        links.append({'source':record[0],'target':record[3],'rank':record[6],'created_at':str(record[7])})
    return links, nodes_dict, list(years_set)

if __name__ == "__main__":
    search_string="How does temperature and humidity affect the transmission of 2019-nCoV?"
    nodes=match_nodes(search_string)
    node_list=get_nodes(nodes)
    links=get_edges(nodes)
    print(node_list)
    print("---")
    print(links)

