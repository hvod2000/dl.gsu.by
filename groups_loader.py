import xml.etree.ElementTree as ET
import os

problem = "problem.xml"


def checkfile(file):
    if not os.path.isfile(file):
        print(f"{file} not found")
        return False
    return True


if not checkfile("task.cfg"):
    exit(1)
if not checkfile(problem):
    problem += ".polygon"
if not checkfile(problem):
    print("error reading xml")
    exit(1)

print(f"reading {problem}")

# extract info from xml
tree = ET.parse(problem)
testset = tree.getroot().findall(".//testset[@name='tests']")[0]
tests = testset.find("./tests")
groups = testset.find("./groups") or []

# tests_info = [(group_number, points_per_test)]
tests = [(t.attrib.get("group", 0), t.attrib.get("points")) for t in tests]
tests_info = [(0 if g == "samples" else int(g), p) for g, p in tests]

# groups_points_policy = {group_number: points-policy}
gs = {g.attrib["name"]: g.attrib["points-policy"] for g in groups}
groups_points_policy = {
    (0 if g == "samples" else int(g)): v for g, v in gs.items()
}

# groups_dependencies = {group_number: dependencies}
groups_dependencies = dict()
for g in groups:
    group_name = g.attrib["name"]
    group_number = 0 if group_name == "samples" else int(group_name)
    groups_dependencies[group_number] = set()
    for dependencies in (child for child in g if child.tag == "dependencies"):
        for dependency in dependencies:
            dependency_group_name = dependency.attrib["group"]
            dependency_group_number = (
                0
                if dependency_group_name == "samples"
                else int(dependency_group_name)
            )
            groups_dependencies[group_number].add(dependency_group_number)

dic = {}
# find tests for every group
for test_ind, (test_group, test_points) in enumerate(tests_info):
    if test_group not in dic:
        dic[test_group] = set()
    dic[test_group].add(test_ind)

# regroup using groups points policy
new_dic = {}
for group, tests in dic.items():
    if (
        group > 0
        and group in groups_points_policy
        and groups_points_policy[group] == "each-test"
    ):
        for test in tests:
            new_dic[len(new_dic)] = {test}
        # raise exception if dependencies are broken after regroup
        if sum(len(deps) for deps in groups_dependencies.values()) > 0:
            raise Exception(
                '"each-test" policy is not compatible with group dependencies'
            )
    else:
        new_dic[len(new_dic)] = tests
dic = new_dic

# calculate points for every group
new_dic = {}
for group, tests in dic.items():
    points = (
        sum(float(tests_info[t][1]) for t in tests)
        if all(tests_info[t][1] is not None for t in tests)
        else None
    )
    new_dic[group] = [points, len(tests)]
dic = new_dic

# read points from "task.cfg" if some points are None
# format: GROUP1_POINTS = points_for_group_1 points_for_group_2 points_for_group_3 ...
if any(group_info[0] is None for group_info in dic.values()):
    with open("task.cfg") as cfg:
        cfg = cfg.read().split("\n")
        GROUP1_POINTS = next(
            line for line in cfg if line.upper().startswith("GROUP1_POINTS")
        )
        points_for_groups = [0] + GROUP1_POINTS.split("=")[1].strip().split(" ")
    for group, group_info in dic.items():
        if group_info[0] is None:
            group_info[0] = float(points_for_groups.pop(0))

total = float(0)
for group, (points, tests) in dic.items():
    print(f"group #{group}:\t{points} points\t{tests} tests")
    total += points
print(f"total points: {total}")

if sum(len(deps) for deps in groups_dependencies.values()) > 0:
    print("\n -- DEPENDENCIES --")
    for group, deps in groups_dependencies.items():
        deps = ", ".join(str(d) for d in deps) if deps else "no dependencies"
        print(f"group #{group}:\t{deps}")
    print()

if os.path.isfile("task.cfg.old"):
    print("found old task.cfg, copying skipped")
else:
    print("making a copy of task.cfg")
    os.system("copy task.cfg task.cfg.old")

lines = []
lines_end = []
skip_line = False
after_end = False
for line in open("task.cfg"):
    if not skip_line:
        lines.append(line)
    if line.lower().startswith("tests_begin"):
        skip_line = True
    if line.lower().startswith("tests_end"):
        after_end = True
    if after_end:
        lines_end.append(line)

if not lines[-2].startswith("NEW_GROUP"):
    lines.insert(-1, "NEW_GROUP = 1\n")

i = 0
while dic.get(i):
    points, tests = dic[i]
    for j in range(tests - 1):
        lines.append("-1\n")
    lines.append(str(int(round(points))) + "\n")
    i += 1
lines += lines_end

# find DEPS_BEGIN and DEPS_END in task.cfg
deps_start = deps_end = 0
while (
    deps_start < len(lines)
    and lines[deps_start].lower().strip() != "deps_begin"
):
    deps_start += 1
if deps_start < len(lines):
    deps_end = deps_start
    while (
        deps_end < len(lines) and lines[deps_end].lower().strip() != "deps_end"
    ):
        deps_end += 1
if not (deps_start < deps_end < len(lines)):
    deps_start = len(lines)
    deps_end = deps_start + 1
    if sum(len(deps) for deps in groups_dependencies.values()) > 0:
        lines += ["deps_begin\n", "deps_end\n"]
cfg_deps = []

# add dependencies to task.cfg
if sum(len(deps) for deps in groups_dependencies.values()) > 0:
    for group, deps in groups_dependencies.items():
        if deps:
            deps = " ".join(str(d) for d in deps)
            cfg_deps.append(f"{group}: {deps}\n")
    lines[(deps_start + 1) : deps_end] = cfg_deps

print("rewriting task.cfg")
with open("task.cfg", "w") as f:
    for line in lines:
        f.write(line)
