import os
import argparse
import sqlite3

from parsers import pemi_processor

def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-d', dest='directory', required=False)
    args = arg_parser.parse_args()

    directory = 'invoices'

    if args.directory:
        assert os.path.exists(args.directory)
        directory = args.directory

    print(f"Searching for pdfs in '{directory}'...")
    found_services = pemi_processor.get_services(directory) 
    print(f"Found {len(found_services)} services in pdf statements") 

    # existing_trans = db_manager.get_existing_trans(db_conn)
    to_add = found_services # - existing_services

    print(f"Adding {len(to_add)} new services to db...")
    for service in found_services:
        print(service)
    # db_manager.add_to_db(db_conn, to_add)


if __name__ == '__main__':
    main()

