
from restriction_enzymes import map_re_sites
from itertools           import combinations
from warnings            import warn
import locale

"""
10 nov. 2014

iterative mapping copied from hiclib

"""

def eq_reads(rd1, rd2):
    """
    Compare reads accounting for multicontacts
    """
    return rd1.split('~', 1)[0] == rd2.split('~', 1)[0]

def get_intersection(fname1, fname2, out_path, verbose=False):
    """
    Merges the two files corresponding to each reads sides. Reads found in both
       files are merged and written in an output file.

    Dealing with multiple contacts:
       - a pairwise contact is created for each possible combnation of the
         multicontacts. The name of the read is extended by '# 1/3' in case
         the reported pairwise contact corresponds to the first of 3 possibles
       - it may happen that different contacts are mapped on a single RE fragment
         (if each are on different end), in which case:
          - if no other fragment from this read are mapped than, both are kept
          - otherwise, they are merged into one longer (as if they were mapped
            in the positive strand)

    :param fname1: path to a tab separated file generated by the function
       :func:`pytadbit.parsers.sam_parser.parse_sam`
    :param fname2: path to a tab separated file generated by the function
       :func:`pytadbit.parsers.sam_parser.parse_sam`
    :param out_path: path to an outfile. It will written in a similar format as
       the inputs
    """
    reads_fh = open(out_path, 'w')
    reads1 = open(fname1)
    line1 = reads1.next()
    header1 = ''
    while line1.startswith('#'):
        if line1.startswith('# CRM'):
            header1 += line1
        line1 = reads1.next()
    read1 = line1.split('\t', 1)[0]

    reads2 = open(fname2)
    line2 = reads2.next()
    header2 = ''
    while line2.startswith('#'):
        if line2.startswith('# CRM'):
            header2 += line2
        line2 = reads2.next()
    read2 = line2.split('\t', 1)[0]
    if header1 != header2:
        raise Exception('seems to be mapped onover different chromosomes\n')
    # setup REGEX to split reads in a single line
    # readex = recompile('((?:[^\t]+\t){6}[^\t]+)')
    # writes header in output
    reads_fh.write(header1)
    # writes common reads
    count = 0
    multiples = {}
    try:
        while True:
            if eq_reads(read1, read2):
                count += 1
                # case we have potential multicontacts
                if '|||' in line1 or '|||' in line2:
                    elts = {}
                    for read in line1.split('|||'):
                        nam, crm, pos, strd, nts, beg, end = read.strip().split('\t')
                        elts.setdefault((crm, beg, end), []).append(
                            (nam, crm, pos, strd, nts, beg, end))
                    for read in line2.split('|||'):
                        nam, crm, pos, strd, nts, beg, end = read.strip().split('\t')
                        elts.setdefault((crm, beg, end), []).append(
                            (nam, crm, pos, strd, nts, beg, end))
                    # write contacts by pairs
                    # loop over RE fragments
                    for elt in elts:
                        # case we have 2 read-frags inside current fragment
                        if len(elts[elt]) == 1:
                            elts[elt] = elts[elt][0]
                        # case all fragments felt into a single RE frag
                        # we take only first and last
                        elif len(elts) == 1:
                            elts[elt] = sorted(
                                elts[elt],
                                key=lambda x: int(x[2]))[::len(elts[elt])-1]
                            elts1 = {elt: elts[elt][0]}
                            elts2 = {elt: elts[elt][1]}
                        # case we have several read-frag in this RE fragment
                        else:
                            # take first and last
                            map1, map2 = sorted(
                                elts[elt],
                                key=lambda x: int(x[2]))[::len(elts[elt])-1]
                            elts[elt] = map1
                            # sum up read-frags in the RE fragment  by putting
                            # them on the same strand
                            if map1[3] == '1':
                                beg = int(map1[2])
                            else:
                                beg = int(map1[2]) - int(map1[4]) - 1
                            if map2[3] == '0':
                                nts = int(map2[2]) - beg
                            else:
                                nts = int(map2[2]) + int(map2[4]) + 1 - beg
                            elts[elt] = tuple(list(elts[elt][:2]) +
                                              [str(beg), '1', str(nts)] +
                                              list(elts[elt][5:]))
                    contacts = len(elts) - 1
                    if contacts > 1:
                        multiples.setdefault(contacts, 0)
                        multiples[contacts] += 1
                        for i, (r1, r2) in enumerate(combinations(elts.values(), 2)):
                            r1, r2 = sorted((r1, r2), key=lambda x: x[1:2])
                            reads_fh.write(r1[0] + (
                                '#%d/%d' % (i + 1, contacts * (contacts + 1) / 2)) +
                                           '\t' + '\t'.join(r1[1:]) + '\t' + 
                                           '\t'.join(r2[1:]) + '\n')
                    elif contacts == 1:
                        r1, r2 = sorted((elts.values()[0], elts.values()[1]),
                                        key=lambda x: x[1:2])
                        reads_fh.write('\t'.join(r1) + '\t' + 
                                       '\t'.join(r2[1:]) + '\n')
                    else:
                        r1, r2 = sorted((elts1.values()[0], elts2.values()[0]),
                                        key=lambda x: x[1:2])
                        reads_fh.write('\t'.join(r1) + '\t' + 
                                       '\t'.join(r2[1:]) + '\n')
                else:
                    r1, r2 = sorted((line1.split(), line2.split()),
                                    key=lambda x: x[1:2])
                    reads_fh.write('\t'.join(r1) + '\t' +
                                   '\t'.join(r2[1:]) + '\n')
                line1 = reads1.next()
                read1 = line1.split('\t', 1)[0]
                line2 = reads2.next()
                read2 = line2.split('\t', 1)[0]
            # if first element of line1 is greater than the one of line2:
            elif locale.strcoll(read1, read2) > 0:
                line2 = reads2.next()
                read2 = line2.split('\t', 1)[0]
            else:
                line1 = reads1.next()
                read1 = line1.split('\t', 1)[0]
    except StopIteration:
        reads1.close()
        reads2.close()
    reads_fh.close()
    if verbose:
        print 'Found %d pair of reads mapping uniquely' % count
    return count, multiples


def get_intersection_dev(fname1, fname2, out_path, verbose=False):
    """
    Merges the two files corresponding to each reads sides. Reads found in both
       files are merged and written in an output file.

    Dealing with multiple contacts:
       - a pairwise contact is created for each possible combnation of the
         multicontacts. The name of the read is extended by '# 1/3' in case
         the reported pairwise contact corresponds to the first of 3 possibles
       - it may happen that different contacts are mapped on a single RE fragment
         (if each are on different end), in which case:
          - if no other fragment from this read are mapped than, both are kept
          - otherwise, they are merged into one longer (as if they were mapped
            in the positive strand)

    :param fname1: path to a tab separated file generated by the function
       :func:`pytadbit.parsers.sam_parser.parse_sam`
    :param fname2: path to a tab separated file generated by the function
       :func:`pytadbit.parsers.sam_parser.parse_sam`
    :param out_path: path to an outfile. It will written in a similar format as
       the inputs
    """
    reads_fh = open(out_path, 'w')
    reads1 = open(fname1)
    line1 = reads1.next()
    header1 = ''
    while line1.startswith('#'):
        if line1.startswith('# CRM'):
            header1 += line1
        line1 = reads1.next()
    read1 = line1.split('\t', 1)[0]

    reads2 = open(fname2)
    line2 = reads2.next()
    header2 = ''
    while line2.startswith('#'):
        if line2.startswith('# CRM'):
            header2 += line2
        line2 = reads2.next()
    read2 = line2.split('\t', 1)[0]
    if header1 != header2:
        raise Exception('seems to be mapped onover different chromosomes\n')
    # setup REGEX to split reads in a single line
    # readex = recompile('((?:[^\t]+\t){6}[^\t]+)')
    # writes header in output
    reads_fh.write(header1)
    # writes common reads
    count = 0
    multiples = {}
    try:
        while True:
            if eq_reads(read1, read2):
                count += 1
                # case we have potential multicontacts
                if '|||' in line1 or '|||' in line2:
                    elts = {}
                    for read in line1.split('|||'):
                        nam, crm, pos, strd, nts, beg, end = read.strip().split('\t')
                        elts.setdefault((crm, beg, end), []).append(
                            (nam, crm, pos, strd, nts, beg, end))
                    for read in line2.split('|||'):
                        nam, crm, pos, strd, nts, beg, end = read.strip().split('\t')
                        elts.setdefault((crm, beg, end), []).append(
                            (nam, crm, pos, strd, nts, beg, end))
                    # write contacts by pairs
                    # loop over RE fragments
                    for elt in elts:
                        # case we have 2 read-frags inside current fragment
                        if len(elts[elt]) == 1:
                            elts[elt] = elts[elt][0]
                        # case all fragments felt into a single RE frag
                        # we take only first and last
                        elif len(elts) == 1:
                            elts[elt] = sorted(
                                elts[elt],
                                key=lambda x: int(x[2]))[::len(elts[elt])-1]
                            elts1 = {elt: elts[elt][0]}
                            elts2 = {elt: elts[elt][1]}
                        # case we have several read-frag in this RE fragment
                        else:
                            # take first and last
                            map1, map2 = sorted(
                                elts[elt],
                                key=lambda x: int(x[2]))[::len(elts[elt])-1]
                            elts[elt] = map1
                            # sum up read-frags in the RE fragment  by putting
                            # them on the same strand
                            if map1[3] == '1':
                                beg = int(map1[2])
                            else:
                                beg = int(map1[2]) - int(map1[4]) - 1
                            if map2[3] == '0':
                                nts = int(map2[2]) - beg
                            else:
                                nts = int(map2[2]) + int(map2[4]) + 1 - beg
                            elts[elt] = tuple(list(elts[elt][:2]) +
                                              [str(beg), '1', str(nts)] +
                                              list(elts[elt][5:]))
                    contacts = len(elts) - 1
                    if contacts > 1:
                        multiples.setdefault(contacts, 0)
                        multiples[contacts] += 1
                        for i, (r1, r2) in enumerate(combinations(elts.values(), 2)):
                            r1, r2 = sorted((r1, r2), key=lambda x: x[1:2])
                            reads_fh.write(r1[0] + (
                                '#%d/%d' % (i + 1, contacts * (contacts + 1) / 2)) +
                                           '\t' + '\t'.join(r1[1:]) + '\t' + 
                                           '\t'.join(r2[1:]) + '\n')
                    elif contacts == 1:
                        r1, r2 = sorted((elts.values()[0], elts.values()[1]),
                                        key=lambda x: x[1:2])
                        reads_fh.write('\t'.join(r1) + '\t' + 
                                       '\t'.join(r2[1:]) + '\n')
                    else:
                        r1, r2 = sorted((elts1.values()[0], elts2.values()[0]),
                                        key=lambda x: x[1:2])
                        reads_fh.write('\t'.join(r1) + '\t' + 
                                       '\t'.join(r2[1:]) + '\n')
                else:
                    r1, r2 = sorted((line1.split(), line2.split()),
                                    key=lambda x: x[1:2])
                    reads_fh.write('\t'.join(r1) + '\t' +
                                   '\t'.join(r2[1:]) + '\n')
                line1 = reads1.next()
                read1 = line1.split('\t', 1)[0]
                line2 = reads2.next()
                read2 = line2.split('\t', 1)[0]
            # if first element of line1 is greater than the one of line2:
            elif locale.strcoll(read1, read2) > 0:
                line2 = reads2.next()
                read2 = line2.split('\t', 1)[0]
            else:
                line1 = reads1.next()
                read1 = line1.split('\t', 1)[0]
    except StopIteration:
        reads1.close()
        reads2.close()
    reads_fh.close()
    if verbose:
        print 'Found %d pair of reads mapping uniquely' % count
    return count, multiples

