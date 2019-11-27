from glob import glob
from subprocess import check_call
import os
from tqdm import tqdm
from os.path import *
from collections import defaultdict
from Bio import SeqIO
import multiprocessing as mp

resource_dir = "/home-user/thliao/data/protein_db/dating_resource"
cdd_tbl = f"{resource_dir}/cog/cddid_all.tbl"
list27_genes = f"{resource_dir}/single.cog.list"
cog_list = set([_.split('\t')[0] for _ in open(list27_genes).read().split('\n') if _])

cdd_num = defaultdict(list)
for row in open(cdd_tbl,'r'):
    if row.split('\t')[1] in cog_list:
        cdd_num[row.split('\t')[1]].append("CDD:%s" % row.split('\t')[0])
cdd_num.pop('TIGR00487')

cog_db = f"{resource_dir}/cog/Cog"
TIGRFAM_db = f"{resource_dir}/TIGRFAM_v14/TIGR00487.HMM"
# ABOVE is the default setting for luolab server.

def run(cmd):
    check_call(cmd,
               shell=True,
               stdout=open('/dev/null','w'),
               stderr=open('/dev/null','w'))

def annotate_cog(raw_protein,cog_out_dir):
    params = []
    for f in glob(raw_protein):
        gname = basename(f).replace('.faa', '')
        # for cdd
        ofile = f'{cog_out_dir}/{gname}.out'
        cmd = f"blastp -query {f} -db {cog_db} -max_hsps 1 -max_target_seqs 1 -num_threads 10 -outfmt 6 -evalue 1e-5 -out {ofile}"
        if not os.path.exists(ofile):
            if not exists(dirname(ofile)):
                os.makedirs(dirname(ofile))
            params.append(cmd)
        # for tigrfam
        ofile = f'{cog_out_dir}/TIGRFAM/{gname}.out'
        cmd = f"hmmscan --tblout {ofile} --acc --noali --notextw --cpu 10 {TIGRFAM_db} {f}"
        if not os.path.exists(ofile):
            if not exists(dirname(ofile)):
                os.makedirs(dirname(ofile))
            params.append(cmd)
    with mp.Pool(processes=5) as tp:
        list(tqdm(tp.imap(run,params),total=len(params)))
        
        
def _get_tophit(gid2locus,top_hit):
                
    if top_hit:
        gid2locus = {k:sorted(v,
                            key=lambda x:x[1])  
                      for k,v in gid2locus.items()}
        gid2locus = {k:[v[0][0]] 
                      if v else [] 
                      for k,v in gid2locus.items()}
    else:
        gid2locus = {k:[_[0] for _ in v] 
                      if v else []
                      for k,v in gid2locus.items()}
    return gid2locus
def _parse_blastp(ofile,match_ids=[],top_hit = False):
    if not match_ids:
        gid2locus = defaultdict(list)
    else:
        gid2locus = {k:[] for k in match_ids}
    for row in open(ofile,'r'):
        sep_v = row.split('\t')
        locus = sep_v[0]
        evalue = sep_v[10]
        if sep_v[1] in match_ids:
            gid2locus[sep_v[1]].append((locus,evalue))
    gid2locus = _get_tophit(gid2locus,top_hit=top_hit)
    return gid2locus

def _parse_hmmscan(ofile,filter_evalue=None,top_hit = False):
    gid2locus = defaultdict(list)

    for row in open(ofile, 'r'):
        if row.startswith('#'):
            continue
        r = row.split(' ')
        r = [_ for _ in r if _]

        gene_id = r[1]
        locus_tag = r[2]
        evalue = float(r[4])
        if filter_evalue and evalue <= filter_evalue:
            gid2locus[gene_id].append((locus_tag, evalue))
        else:
            gid2locus[gene_id].append((locus_tag, evalue))
    gid2locus = _get_tophit(gid2locus,top_hit=top_hit)
    return gid2locus

def parse_annotation(cog_out_dir,top_hit = False):
    # for cdd
    _cdd_match_ids = set([_ for vl in cdd_num.values() for _ in vl])
    genome2cdd = defaultdict(lambda:defaultdict(list))
    
    # cdd annotations
    cdd_anno_files = glob(join(cog_out_dir,'*.out'))
    for ofile in tqdm(cdd_anno_files):
        gname = basename(ofile).replace('.out','')
        locus_dict = _parse_blastp(ofile=ofile,
                                   match_ids=_cdd_match_ids,
                                   top_hit=top_hit)
        genome2cdd[gname].update(locus_dict)
    # tigrfam annotations
    tigrfam_anno_files = glob(join(cog_out_dir,'TIGRFAM','*.out'))
    for ofile in tqdm(tigrfam_anno_files):
        gname = basename(ofile).replace('.out','')
        locus_dict = _parse_hmmscan(ofile=ofile,
                                   top_hit=top_hit)
        genome2cdd[gname].update(locus_dict)
    return genome2cdd

# extract protein
def write_cog(outdir,genome2cdd,raw_proteins,genome_ids=[],get_type='prot'):
    genome2seq = {}
    if not genome_ids:
        genome_ids = list(genome2cdd)
    gene_ids = set([_ for vl in genome2cdd.values() for _ in vl])
    pdir = dirname(expanduser(raw_proteins))
    if get_type == 'nuc':
        suffix = 'ffn'
    elif get_type == 'prot':
        suffix = 'faa'
    else:
        raise Exception
    if not exists(outdir):
        os.makedirs(outdir)
    tqdm.write('get sequence file')
    for genome_name in tqdm(genome_ids):
        g_dict = genome2cdd[genome_name]
        gfile = f'{pdir}/{genome_name}.faa'
        new_pdir = abspath(dirname(dirname(realpath(gfile))))
        gfile = f"{new_pdir}/tmp/{genome_name}/{genome_name}.{suffix}"

        if exists(gfile):
            _cache = {record.id:record
                      for record in SeqIO.parse(gfile,format='fasta')}
            seq_set = {k:[_cache[_]
                       for _ in v
                       if _ in _cache]
                    for k,v in g_dict.items()}
            genome2seq[genome_name] = seq_set
            
    # concat/output proteins
    tqdm.write('write out')
    for each_gene in tqdm(gene_ids):
        gene_records = []
        for gname, seq_dict in genome2seq.items():
            get_records = seq_dict.get(each_gene,[])
            for record in get_records:
                record.name = gname
            gene_records+=get_records
        unique_cdd_records = [] 
        [unique_cdd_records.append(record) 
         for record in gene_records 
         if record.id not in [_.id 
                              for _ in unique_cdd_records]]  
        
        with open(join(outdir,f"{each_gene.replace('CDD:','')}.faa"),'w') as f1:
            SeqIO.write(unique_cdd_records,f1,format='fasta-2line')



# def perform_iqtree(outdir):
#     script = expanduser('~/bin/batch_run/batch_mafft.py')
#     run(f"python3 {script} -i {outdir} -o {outdir}")

#     script = expanduser('~/bin/batch_run/batch_tree.py')
#     run(f"python3 {script} -i {outdir} -o {outdir} -ns newick -use fasttree")

def stats_cog(genome2genes):
    gene_ids = set([_ for vl in genome2cdd.values() for _ in vl])
    
    gene_multi = {g:0 for g in gene_ids}
    for genome, pdict in genome2genes.items():
        for gene, seqs in pdict.items():
            if len(seqs) >= 2:
                gene_multi[gene] += 1
    gene_Ubiquity = {g:0 for g in gene_ids}
    for genome, pdict in genome2genes.items():
        for gene, seqs in pdict.items():
            gene_Ubiquity[gene] += 1
    
    backbone_gene = {g:0 for g in gene_ids}
    for gene in gene_ids:
        
    #for genome, pdict in genome2genes.items():
        if all([pdict.get(gene,[]) for _, pdict in genome2genes.items()]):
            backbone_gene[gene] += 1
                
    return gene_multi,gene_Ubiquity,backbone_gene

            
if __name__ == "__main__":
    import sys
    # usage :
    # extract_cog.py 'raw_genome_proteins/*.faa' ./target_genes ./conserved_protein
    if len(sys.argv) >= 2:
        raw_proteins = sys.argv[1]
        annotation_dir = sys.argv[2]
        outdir = sys.argv[3]
    else:
        raw_proteins = expanduser('~/data/nitrification_for/dating_for/raw_genome_proteins/*.faa')
        annotation_dir = expanduser('~/data/nitrification_for/dating_for/target_genes_blastp')
        outdir = expanduser('~/data/nitrification_for/dating_for/cog25_multiple')
        gids = open(expanduser('~/data/nitrification_for/dating_for/bac120_annoate/remained_ids_fullv1.list')).read().split('\n')
    annotate_cog(raw_proteins, annotation_dir)
    genome2cdd = parse_annotation(annotation_dir,top_hit=True)
    write_cog(outdir,genome2cdd,raw_proteins,genome_ids=gids,get_type='prot')
    write_cog(outdir+'_nuc',genome2cdd,raw_proteins,genome_ids=gids,get_type='nuc')
    
    _subgenome2cdd = {k:v for k,v in genome2cdd if k in set(gids)}
    gene_multi,gene_Ubiquity,backbone_gene = stats_cog(_subgenome2cdd)