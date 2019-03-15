#!/usr/bin/env python3

import argparse
import re
import sys
import pysam
from Mikado.transcripts.transcript import Transcript
from collections import Counter


def to_bam(string):
    return pysam.AlignmentFile(string, mode="rb")


def main():
    parser = argparse.ArgumentParser("Script to convert from BAM to GTF, for PB alignments")
    parser.add_argument("--strict", action="store_true", default=False,
                        help="Switch. If set, this script will never output multiexonic transcripts \
                        without a defined strand.")
    parser.add_argument("--outfmt", choices=["gtf", "bed12"], default="gtf")
    parser.add_argument("bam", type=to_bam, help="Input BAM file")
    parser.add_argument("out", nargs="?", default=sys.stdout, type=argparse.FileType("wt"),
                        help="Optional output file")
    args = parser.parse_args()

    # M 0 alignment match (can be a sequence match or mismatch)
    # I 1 insertion to the reference
    # D 2 deletion from the reference
    # N 3 skipped region from the reference
    # S 4 soft clipping (clipped sequences present in SEQ)
    # H 5 hard clipping (clipped sequences NOT present in SEQ)
    # P 6 padding (silent deletion from padded reference)
    # = 7 sequence match
    # X 8 sequence mismatch

    name_counter = Counter()

    for record in args.bam:
        record.cigar = [(key, val) if key not in (7, 8) else (0, val) for key, val in record.cigar]

        try:
            start, end = record.reference_start, record.get_blocks()[-1][1]
        except IndexError:
            continue

        current = start

        exons = []
        current_exon = None

        r_length = record.inferred_length  # Read length
        # Upper because of STAR
        edit_distance = [_[1] for _ in record.tags if _[0].upper() == "NM"][0]  # Excluding clipping
        matches = 0
        alen = 0

        for cigar,length in record.cigartuples:
            if cigar in (4,5):  # Insertion, clipping (soft or hard)
                continue
            elif cigar == 1:
                alen += length
            elif cigar == 3:  # Intron
                if current_exon is None:
                    continue # Read positioned at the end/beginning of scaffold
                # assert current_exon is not None
                exons.append(current_exon)
                current_exon = None
                current += length
            elif cigar in (0, 2):  # Match or deletion
                if current_exon is None:
                    current_exon = (current + 1, current + length)
                else:
                    current_exon = (current_exon[0], current_exon[1] + length)
                current += length
                if cigar == 0:
                    matches += length
                    alen += length

        md_found = False
        snps = 0
        for tag in record.tags:
            if tag[0] == "MD":
                md_found = True
                snps = sum(len(_) for _ in re.split("[0-9]*", tag[1]) if not _.startswith("^"))
                break

        if md_found:
            identity = round(100 * (matches - snps) / r_length, 2)
        else:
            identity = "NA"

        coverage = round(100 * alen / r_length, 2)

        exons.append(current_exon)
        # This is clearly a mistake
        if current != end:
            msg = """{0}, {1}, {2}
Cigar tuples: {3}
Cigar string: {4}
Blocks: {5}
Exons: {6}
            """.format(current, end, end-current,
                       record.cigartuples,
                       record.cigarstring,
                       record.get_blocks(),
                       exons)
            print(AssertionError(msg), file=sys.stderr)
            #            raise AssertionError(msg)
            continue

        transcript = Transcript(accept_undefined_multi=(not args.strict))
        if name_counter.get(record.query_name):
            name = "{}_{}".format(record.query_name, name_counter.get(record.query_name))
        else:
            name = record.query_name

        transcript.id = name
        transcript.parent = transcript.attributes["gene_id"] = "{0}.gene".format(name)
        name_counter.update([record.query_name])

        transcript.exons = exons
        transcript.attributes["identity"] = identity
        transcript.attributes["coverage"] = coverage
        transcript.attributes["cigar"] = record.cigarstring
        transcript.chrom = args.bam.getrname(record.rname)
        transcript.score = record.mapq
        if len(transcript.exons) == 0:
            continue

        assert len(transcript.exons) > 0
        try:
                transcript.start = min(x[0] for x in transcript.exons)
                transcript.end = max(x[1] for x in transcript.exons)
        except IndexError:
                raise IndexError(transcript.exons)

        transcript.source = "bam2gtf"

        transcript.attributes.update(dict((tag,str(value)) for tag,value in record.get_tags()))

        if "XS" in transcript.attributes:
            transcript.strand = transcript.attributes["XS"]
        else:
            if record.is_reverse:
                transcript.strand = "-"
            else:
                transcript.strand = "+"

        print(transcript.format(args.outfmt), file=args.out)


main()
