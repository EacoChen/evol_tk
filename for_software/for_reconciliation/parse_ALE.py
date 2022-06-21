
from ete3 import Tree
import io
import pandas as pd


def read_rec(rec_file):
    # receving the file with suffix '.uml_rec' generated by the ALEml_undated
    
    rows = open(rec_file).read().strip().split('\n')
    s_tree = [_ for _ in rows if _.startswith('S:')]
    assert len(s_tree) == 1
    stree = Tree(s_tree[0].replace('S:','',1).strip(),format=1)
    
    event_counts_idx = 0
    event_counts_idx = [idx for idx,_ in enumerate(rows) if _ == "# of	 Duplications	Transfers	Losses	Originations	copies"]
    assert len(event_counts_idx) == 1
    df = pd.read_csv(io.StringIO('\n'.join(rows[event_counts_idx[0]+1:-1])),sep='\t',header=None,dtype=str)
    df = df.set_index(1)
    df.columns = ["types"] + "Duplications	Transfers	Losses	Originations	copies".split('\t')
    for col in df.columns[1:]:
        df.loc[:,col] = df[col].astype(float)
    return df,stree

def format_with_reftree(df,stree,ref_tree):
    reftree = Tree(ref_tree,format=3)
    all_leaves = {_.split('_')[1]:_ for _ in reftree.get_leaf_names()}
    leaves2n = {tuple(sorted(n.get_leaf_names())):n.name for n in reftree.traverse()}
    
    name_convertor = {}
    for n in stree.get_leaves():
        name_convertor[n.name] = all_leaves[n.name]
        n.name = all_leaves[n.name]
        
    for n in stree.traverse():
        if not n.is_leaf():
            formatted_name = leaves2n.get(tuple(sorted(n.get_leaf_names())))
            if formatted_name is not None:
                name_convertor[n.name] = formatted_name
                n.name = formatted_name
            else:
                print(n)
    df.index = [name_convertor[_] for _ in df.index]
    return df,stree


if __name__ == '__main__':
    #main()
    ref_tree = "/mnt/ivy/thliao/project/AOB/analysis/20210713_repeat/reconciliate_ALE/stree.newick"
    rec_file = "/mnt/ivy/thliao/project/AOB/analysis/20210713_repeat/reconciliate_ALE/xmoCBA_renamed_5.ufboot.ale.uml_rec"
    df,stree = read_rec(rec_file)
    
    
    
    