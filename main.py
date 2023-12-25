#	main.py
#
#	Non-Deterministic Processor (NDP) - efficient parallel SAT-solver
#	Copyright (c) 2023 GridSAT Stiftung
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU Affero General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU Affero General Public License for more details.
#
#	You should have received a copy of the GNU Affero General Public License
#	along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#	GridSAT Stiftung - Georgstr. 11 - 30159 Hannover - Germany - ipfs: gridsat.eth/ - info@gridsat.io
#

import os, sys
import time
import argparse, textwrap
import ray
import logging

# Initialize Ray with the current directory as the working directory
def initialize_ray():
	if not ray.is_initialized():
		current_dir = os.path.dirname(os.path.abspath(__file__))
		# Set Ray's logging level to only show errors
		ray.init(runtime_env={"working_dir": current_dir}, logging_level=logging.ERROR)
		cluster_resources = ray.cluster_resources()
		num_cpus = cluster_resources.get("CPU", 1)  # Defaults to 1 if not available
		print(f"\n\n\nNDP started.")
		return cluster_resources, num_cpus

cluster_resources, num_cpus = initialize_ray()

from audioop import mul
from copy import deepcopy
from Multiply import Multiply
from Set import *
from Clause import *
from PatternSolver import *
from InputReader import InputReader
import configs
import traceback
from Factorizer import Factorizer
from byebye import bye_art

# todo:
#
# - Handle if input has [x, -x]. What I did now is to normalize the clause once it get read. However, this will not enable us to
#   view the initial set provided. Will see only the normalized version. The solution is to write normalize() method in each Clause and Set classes.
#   and in the evaluation loop, we call the method normalize() before to_lo_condition(). However, do we need to normalize each set? or it's just the root set?
#   This needs to be thought of well because we don't want to add extra time in the evaluation loop if we won't need normalization except for the root set.
#   Currently it works fine with the current implementation as it focuses only on root, but we just don't save the unnormalized version for the root set.   
#  - enable multiple Ray Clusters
#  - enable GPU

def display_ascii_art(ascii_art):
	print(ascii_art)

# a class to represent the CNF graph
class CnfGraph:

	content = None

	def __init__(self, content = None):
		self.content = content

	def print_node(self):
		logger.info(self.content)


def Main(args):
	# determine input type/format
	input_type = None
	input_content = None

	if args.line_input:
		input_type = INPUT_SL
		input_content = args.line_input

	elif args.line_input_file:
		input_type = INPUT_SLF
		input_content = args.line_input_file

	elif args.dimacs:
		input_type = INPUT_DIMACS
		input_content = args.dimacs
		
	# Determine the input file name
	input_file_name = None
	if args.line_input_file or args.dimacs:
		input_file_name = os.path.basename(input_content.name) if hasattr(input_content, 'name') else None

	# begin logic
	CnfSet = None
	try:
		input_reader = InputReader(input_type, input_content)
		CnfSet = input_reader.get_cnf_set()

		# Tasks: Factorization
		if args.factorize:
			fact = Factorizer()
			if not fact.preprocess_set(CnfSet):
				args.factorize = False

		if args.multiply:
			mul = Multiply()
			if not mul.preprocess_set(CnfSet, args.multiply[0], args.multiply[1]):
				args.multiply = False
				sys.exit(0)

			# check if any clause evaluated to False afer substitution
			for cl in CnfSet.clauses:
				if cl.value == False:
					logger.info("The input set is NOT satisfiable with input factors.")
					logger.info(f"The input numbers {args.multiply[0]} and {args.multiply[1]} can't be multiplied on the input CNF")
					sys.exit(0)

		# copy the cnf to be used in verification step if needed as the CNF will be subject to rename and manipulation later.
		originalCnf = deepcopy(CnfSet)
		# start processing the root set
		if len(CnfSet.clauses) > 0 or CnfSet.value != None:
			PAT = PatternSolver(args=args, problem_id=CnfSet.get_hash().hex(), cluster_resources=cluster_resources, input_file=input_file_name)
			PAT.solve_set(CnfSet)

			# save solution in a file
			if args.output_solution_file and PAT.solution:
				solution = PAT.format_solution(PAT.solution)
				file_name = PAT.problem_id

				# if input is a file
				if input_type != args.line_input:
					file_name = os.path.splitext(input_content.name)[0]

				file_name += '_' + args.mode
				file_name += '.sol'
				fout = open(file_name, 'w')
				fout.write(solution)
				fout.close()
				logger.info(f"Solution written to: {file_name}")

			# verify the solution
			if args.verify and PAT.solution:
				if PAT.verify_solution(originalCnf, PAT.solution):
					logger.info("Solution is VERIFIED!\n\n\n\n")
				else:
					logger.info("The solution is NOT correct! ****")


	except Exception as e:
		logger.critical("Error - {0}".format(str(e)))
		logger.critical("Error - {0}".format(traceback.format_exc()))



if __name__ == "__main__":

	start_time = time.time()
	class Formatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter): pass
	parser = argparse.ArgumentParser(description="NDP [OPTIONS]", formatter_class=argparse.RawTextHelpFormatter)
	group1 = parser.add_mutually_exclusive_group()
	group1.add_argument("-v", "--verbos", help="Verbos", action="store_true")
	group1.add_argument("-vv", "--very-verbos", help="Very verbos", action="store_true")
	group1.add_argument("-q", "--quiet", help="Quiet mode = no subprocess output.", action="store_true")
	group1.add_argument("-qn", "--quiet-but-unique-nodes", help="Quiet mode. Except outputting number of unique nodes.", action="store_true")
	group2 = parser.add_mutually_exclusive_group(required=True)
	group2.add_argument("-l", "--line-input", type=str, help="Represent the input set in one line. Format: a|b|c&d|e|f ...")
	group2.add_argument("-lf", "--line-input-file", type=argparse.FileType('r'), help="Represent the input set in one line stored in a file. Format: a|b|c&d|e|f ...")
	group2.add_argument("-d", "--dimacs", type=argparse.FileType('r'), help="File name to contain the set in DIMACS format. See https://bit.ly/dimcasf")
	parser.add_argument("-g", "--output-graph-file", type=str, help="Output graph file in Graphviz format")
	parser.add_argument("-s", "--output-solution-file", action="store_true", help="Output solution file.")
	parser.add_argument("-ns", "--no-stats", help="Short concise output - no stats - this will disable the global database option.", action="store_true")
	parser.add_argument("-t", "--threads", type=int, help="Number of threads. Value 1 = no multithreading, 0 = max concurrent available threads. This option will implicitly enable the global DB.", default=0)
	parser.add_argument("-e", "--exit-upon-solving", help="Exit whenever a solution is found.", action="store_true")
	parser.add_argument("-verify", "--verify", help="Verify the solution at the end, if any.", action="store_true")
	parser.add_argument("-rdb", "--use-runtime-db", help="Use database for set lookup in table established only for the current cnf", action="store_true")
	parser.add_argument("-gdb", "--use-global-db", help="Use database for set lookup in global sets table", action="store_true")
	parser.add_argument("-gnm", "--gdb-no-mem", help="Don't load hashes from global DB into memory. Only use if gdb gets huge and doesn't fit memory. (slower)", action="store_true")
	parser.add_argument("-z", "--sort-by-size", help="Always sort clauses by size in ascending order.", action="store_true")
	parser.add_argument("-sm", "--start-mode", help="Use mode while prepare sub-processes (options as -m)", choices=['flo', 'flop', 'lo', 'lou', 'normal'], default=None)
	parser.add_argument("-thief", "--thief-method", help="VERY effizient for FACT of Purdom-Sabry input format: Always sort clauses by length and initial index.", action="store_true")
	parser.add_argument("-fact", "--factorize", help="Factorize the input number if not prime.", action="store_true")
	parser.add_argument("-mult", "--multiply", nargs=2, type=int, help="Multiply two numbers with bit-range. NOTE: will not generate total MULT-circuit!")
	parser.add_argument("-m", "--mode", help=textwrap.dedent('''\nSolution modi:\n
	  L.O. condition = Linearily Ordered: all variables appear in the ascending order
	L.O.U. condition = Linearily Ordered Unsorted: clause Set L.O. but unsorted\n
	   flo: all nodes converted to L.O. (default)
	  flop: all nodes converted to L.O. with clauses sorted per size.
	    lo: only the root node is converted to L.O. with the rest converted to L.O.U.
	   lou: all nodes converted to L.O.U. condition.
	normal: no preprocessing except ascending sorting of VARs within each clause.\n
			'''), choices=['flo', 'flop', 'lo', 'lou', 'normal'], default="flo")
	parser.add_argument('--version', action='version', version='%(prog)s ') # can use GitPython to automatically get latest tag here
	parser.add_argument("-b", "--bye-art", help="Opt-out of displaying ASCII art at the end.\n\n", action="store_true")

	# The algorithm
	# --------------
	# START:
	# if FLOP:
	#     place unit clauses first
	# rename vars
	# sort within clauses
	# if FLO or FLOP or (LO root node only):
	#     sort clauses()

	# check if it meets LO condition, if not go to step START


	args = parser.parse_args()

	if args.quiet_but_unique_nodes:
		args.quiet = True

	if args.quiet:
		logger.setLevel(logging.CRITICAL)

	# if threads is set, enable gdb
	# A long note regarding multithreading and gdb:
	#---------------------------------------------

	# When we solve a problem using multithreading/processes, each thread will process a subtree.
	# All thread should check a common storage (gdb in this case) to check for common nodes. This check
	# will avoid processing of a subtree that's been already processed by another thread. This is a major
	# contribution of the theory behind the solution of course. However, in order to achieve that, each
	# thread need to check the DB for "every node" it processes. Let's call the time required for this
	# operation D time, whereas if the thread the time required to process the node is P time.
	# So without the checking of the common node, the thread will spend P x n (n is # of nodes in the tree)
	# to process the tree, whereas with common DB, it'll need (P + D) x n` (where n` is number of unique nodes)
	# So the idea here is that in order to make sense to have the DB of common nodes, the cost of processing the
	# common subtree must be larger than D x n`. In other words, P x n`` > D x n`. Where n`` is the size of the
	# common subtree(s).
	# That being said, it's been found that almost always, the common subtrees are far less than unique ones.
	# Also, for most of nodes, especially on LOU mode where bringing the node to LO condition requires only one
	# iteration, P is very small that it's less than D time.
	# This concludes the fact that P x n`` < D x n` and the cost of having common storage "in the current implementation"
	# is bad.
	# Recommendations:
	# - We need another common nodes storage different than postgres when checking the existence of the node is less than processing it.
	# - The above conclution is valid by experiment for LOU, and partially for LO. We need to do more experiemnts for LO, FLO and FLOP
	# where processing a node can take longer than LOU to draw the same conclusion, otherwise the flag to use gdb can be automatically set
	# with these modes and problem size.
	# - For now, let's disable the automatic activation of gdb with multithreading.
	#
	# otherwise if we want to use gdb, we can explicitly set the commandline option to do so.

	# if args.threads > 1:
	#     args.use_global_db = True


	if args.threads < 0:
		logger.info("Option -t must be a positive number.")
		parser.print_help()
		sys.exit(3)
		
	# Determine the maximum number of CPUs available
	max_cpus = os.cpu_count() if not ray.is_initialized() else int(cluster_resources.get("CPU", 1))

	# Check if the -t argument is set and exceeds the maximum CPUs available
	if args.threads and args.threads > max_cpus:
		response = input(f"The specified number of threads (-t {args.threads}) exceeds the maximum available CPUs ({max_cpus}). "
						"Would you like to use the maximum available CPUs instead? (y/n): ").strip().lower()
		if response == "y":
			args.threads = max_cpus
			print(f"Setting number of threads to the maximum available CPUs: {max_cpus}")
		else:
			print("Please specify a lower value for -t or remove the -t option to use the maximum available CPUs.")
			sys.exit(1)
		
	# at least one input must be provided
	if args.line_input == None and args.line_input_file == None and args.dimacs == None:
		logger.info("No input provided. Please provide any of the input arguments.")
		parser.print_help()
		sys.exit(3)

	# only one input must be provided
	if (args.line_input and args.line_input_file) or (args.line_input and args.dimacs) or (args.dimacs and args.line_input_file):
		logger.info("Please provide only one input.")
		parser.print_help()
		sys.exit(3)

	# only use -gnm if -gdb is set
	if args.gdb_no_mem and not args.use_global_db:
		parser.error('-gnm/--gdb-no-mem MUST be used with -gdb/--use-global-db option')


	if args.multiply and ((args.multiply[0] <= 1) or (args.multiply[1] <= 1)):
		parser.error('-mult/--multiply option MUST be used with integers > 1')

	if args.verbos:
		logger.setLevel(logging.INFO)
	elif args.very_verbos:
		logger.setLevel(logging.DEBUG)
	elif args.quiet:
		logger.setLevel(logging.CRITICAL)

	if args.start_mode is None:
		args.start_mode = args.mode

	Main(args)

	if not args.bye_art:
		display_ascii_art(bye_art)
	logger.info('\nalien-tech at its best. but better.\n\n\n')

	# Set the global logging level to CRITICAL to suppress lower-level logs
	logging.getLogger().setLevel(logging.CRITICAL)
