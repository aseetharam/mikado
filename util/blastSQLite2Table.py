#!/usr/bin/env python3

import sys, os,argparse
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from shanghai_lib.serializers.blast_utils import Hit
from sqlalchemy import create_engine
from sqlalchemy.orm.session import sessionmaker

def main():

	parser=argparse.ArgumentParser("Script to convert the BlastXML output into a tabular format.")
	parser.add_argument("db", type=str, help="DB file to parse.")
	parser.add_argument("out", type=argparse.FileType("w"), default=sys.stdout,
			    nargs='?', help="Optional output file. Default: %(default)s")

	args=parser.parse_args()

	engine=create_engine("sqlite:///{0}".format(args.db))
	session=sessionmaker()
	session.configure(bind=engine)
	current_session=session()

	for hit in current_session.query(Hit):
		print(hit)
		for hsp in hit.hsps:
			print("\t", hsp)


if __name__=='__main__': main()