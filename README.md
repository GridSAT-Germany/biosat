README.md

Bio SAT-solver
Copyright (c) 2023 GridSAT Stiftung

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

GridSAT Stiftung - Georgstr. 11 - 30159 Hannover - Germany - ipfs: gridsat.eth/ - info@gridsat.io
<br><br/>
##
## Bio SAT-solver Features


#### Multiprocessing and Ray Integration
- Efficient multiprocessing on single machines.
- Ray framework for efficient parallel processing on machine clusters.
- Enables large-scale SAT problem solving.

#### Optimum Idle CPU Utilization
The NDP architecture is designed to minimize idle CPU time. It dynamically adjusts task distribution based on available resources, ensuring that all CPUs are efficiently utilized throughout the problem-solving and statistics processes with maximized throughput in HPC environments.

#### Unlimited Linear Scalability
The solver scales linearly with the addition of more computing resources maintaining consistent performance gains.

#### SAT-Solving Options and Script Customization
- Supports various SAT-solving modes, catering to different problem classes.
- Flexible input options: line input, file input, and DIMACS format.
- Customizable script options for enhanced user control and experience.

#### Comprehensive Statistics and Insights
The NDP generates detailed statistics that provide insights into the solving process. Apart the verified solution, statistics include, e.g., a problem ID hash, zulu timestamp, input-file info incl. #VARs and clauses, data on unique nodes, redundant subtrees, memory usage, and # of CPUs.

##
## NDP LINUX Installation with Ray

<br><br/>
#### Install NDP


to [DIRECTORY], e.g.: /NDP
git clone https://github.com/YOUR-USERNAME/NDP-blueprint-thief or download .zip here

##### Prepare system virtualenv

screen session (best practice), e.g.:
```bash
screen -S NDP
```
install Python 3 package manager (pip) and libraries for PostgreSQL database connections with performance monitoring tools for Linux:
```bash
sudo apt install python3-pip libpq-dev sysstat
```

##### Create virtual environment (virtualenv)

```bash
cd <path_to_directory>

virtualenv <dir_name>
```

##### Activate and update virtualenv

```bash
source <dir_name>/bin/activate
```
#####
##### Install Ray and other required tools

```bash
pip install -r requirements.txt
```

For further info on Ray check [Ray Repo](https://github.com/ray-project/ray) and the [Ray documentation](https://docs.ray.io).


<br><br/>
#### Startup RAY for multi-processing on cluster
(*Note: NDP also runs on single machine without Ray - just go to the "Run solver" section below and skip "Startup Ray"*)

##### Start head node without Ray Dashboard

Example initialization with 4 CPUs as system reserves - configure as appropriate:
```bash
export RAY_DISABLE_IMPORT_WARNING=1
CPUS=$(( $(lscpu --online --parse=CPU | egrep -v '^#' | wc -l) - 4 ))
ray start --head --include-dashboard=false --disable-usage-stats --num-gpus=0 --num-cpus=$CPUS
```

##### Start head node with Ray Dashboard

Example initialization with 4 CPUs as system reserves - configure as appropriate:
```bash
export RAY_DISABLE_IMPORT_WARNING=1
CPUS=$(( $(lscpu --online --parse=CPU | egrep -v '^#' | wc -l) - 4 ))
ray start --head --include-dashboard=true --dashboard-host=0.0.0.0 --disable-usage-stats --num-gpus=0 --num-cpus=$CPUS
```

##### Start worker nodes

Example initialization with 2 CPUs system reserves - configure as appropriate:
```bash
export RAY_DISABLE_IMPORT_WARNING=1
CPUS=$(( $(lscpu --online --parse=CPU | egrep -v '^#' | wc -l) - 2 ))
ray start --address='MASTER-IP:6379' --redis-password='MASTER-PASSWORT' --num-gpus=0 --num-cpus=$CPUS
```
<br><br/>
#### Run solver

Example in verbos with L.O.U. condition, max #CPUs, sort by size for best MULT-circuit of [Purdom-Sabry DIMACS-input format](https://cgi.luddy.indiana.edu/~sabry/cnf.html),
and output verification (more info available in published paper [resources](https://gridsat.eth.link/resources.html) and via NDP help):

```bash
python3 main.py -v -d [dir_name]/[CNF/DIMACS] -m lou -z -verify
```

Example in verbos with L.O.U. condition, 256 #CPUs, -thief for best FACT of [Purdom-Sabry DIMACS-input format](https://cgi.luddy.indiana.edu/~sabry/cnf.html), and output verification:

```bash
python3 main.py -v -d [dir_name]/[CNF/DIMACS] -m lou -thief -t256 -verify
```

<br><br/>
#### NDP help

```bash
python3 main.py -h
```


<br><br/>
#### Starter tools

Some helpers with example paths and inputs to easily run the processes and environments provided you configured your scripts (e.g. AWS):

```bash

# .bin/ray.sh
sudo su - [user_name]

# .bin/ray-auto.sh
sudo -u [user_name] -i /bin/bash -i -c ray-auto.sh

# .bin/node.sh
ssh -i $HOME/.ssh/AWS.pem "node$1"

# .bin/node-up.sh
ssh -i $HOME/.ssh/AWS.pem "node$1" -t .bin/ray-auto.sh

# run and log unbuffered (need expect-dev installed)
CORES="0001"; BITS="14"; ( echo "START: `date`"; echo ""; unbuffer python3 main.py -v -d inputs/Multi"$BITS"bit.txt -m lou -t $CORES 2>/dev/null ; echo "" ; echo "ENDE: `date`" ) | tee logs/$(date "+%Y-%m-%d")_Multi"$BITS"bit-$CORES-Cores.txt

# run and start on [HEADNODE]
cd $HOME/myDirectory; source __venv__/bin/activate ; PATH=$PATH:/home/myDirectory/bin ray-auto.sh [HEADNODE] 8

# run and start on a [NODE]
cd $HOME/myDirectory; source __venv__/bin/activate ; PATH=$PATH:/home/myDirectory/bin ray-auto.sh [NODE] 22

```
