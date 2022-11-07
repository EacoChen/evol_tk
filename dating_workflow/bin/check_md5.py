"""
check the md5sum generated by ncbi-genome-download

"""

import hashlib
import os
from glob import glob
from os.path import join, exists, basename, dirname, expanduser, abspath

import click
from tqdm import tqdm

HOME = os.getenv("HOME")


def parse(MD5SUMS):
    md5sum_dict = [_ for _ in open(MD5SUMS).read().split('\n') if _]
    md5sum_dict = {_.split(' ')[-1].replace('./', ''): _.split(' ')[0]
                   for _ in md5sum_dict}
    return md5sum_dict


def iterative_check_md5(indir):
    all_dirs = glob(join(indir, 'GC*'))
    tqdm.write(f"In total, {indir} contain {len(all_dirs)} children directory.")
    failed_files = []
    tqdm.write("Start checking on those md5sum")
    for cdir in tqdm(all_dirs):
        if not exists(join(cdir, 'MD5SUMS')):
            failed_files.append(cdir)
            continue
        md5sums_file = join(cdir, 'MD5SUMS')
        md5sum_dict = parse(md5sums_file)
        for gz_f in glob(join(cdir, '*.gz')):
            name = basename(gz_f)
            md5 = hashlib.md5(open(gz_f, 'rb').read()).hexdigest()
            if md5 != md5sum_dict[name]:
                failed_files.append(cdir)
    failed_IDs = list(set([basename(_) for _ in failed_files]))
    return failed_IDs


def process_path(path):
    if not '/' in path:
        path = './' + path
    if path.startswith('~'):
        path = expanduser(path)
    if path.startswith('.'):
        path = abspath(path)
    return path


@click.command(help="""
accept a input directory to traverse its descending directory and check their md5sum
""")
@click.option("-i", "indir", help="input directory [./genbank/bacteria]", default="./genbank", )
@click.option("-o", "ofile", help="output file which stodge paths", default="./failed_ids", )
def cli(indir, ofile, ):
    indir = process_path(indir)
    ofile = process_path(ofile)
    if not exists(indir):
        raise IOError("input dir doesn't exist")
    if not exists(dirname(ofile)):
        os.mkdir(dirname(ofile))
    failed_IDs = iterative_check_md5(indir)
    with open(ofile, 'w') as f1:
        f1.write('\n'.join(failed_IDs))


if __name__ == "__main__":
    cli()
