"""
Inside conditions.json, you will see a subset of UNSW courses mapped to their
corresponding text conditions. We have slightly modified the text conditions
to make them simpler compared to their original versions.

Your task is to complete the is_unlocked function which helps students determine
if their course can be taken or not.

We will run our hidden tests on your submission and look at your success rate.
We will only test for courses inside conditions.json. We will also look over the
code by eye.

NOTE: We do not expect you to come up with a perfect solution. We are more interested
in how you would approach a problem like this.
"""
import re
import json
from abc import ABC, abstractmethod

dict_precedence = {
    'in': 1,
    'or': 2,
    'and': 2,
    '(': 2,
    ')': 2,
}
composites = ["in", "or", "and"]
course_pattern = r'[a-zA-Z]{4}\d{4}'

# NOTE: DO NOT EDIT conditions.json
with open("./conditions.json") as f:
    CONDITIONS = json.load(f)
    f.close()


def is_unlocked(courses_list, target_course):
    """Given a list of course codes a student has taken, return true if the target_course
    can be unlocked by them.

    You do not have to do any error checking on the inputs and can assume that
    the target_course always exists inside conditions.json

    You can assume all courses are worth 6 units of credit
    """
    req = None
    match_composites = re.compile("|".join(composites))

    # Case 1: No Conditions
    if not CONDITIONS[target_course]:
        return True
    # Case 2: Conditions exist, but no courses completed
    elif CONDITIONS[target_course] and not courses_list:
        return False
    else:
        # Normalise requirements
        expr = CONDITIONS[target_course]
        req = " ".join(expr.lower().split())

        # Remove pre-requisites tag
        match_prereq = r'pre.*: '
        req = re.sub(match_prereq, '', req, re.I)

        expression = []
        last_start = 0
        for match in match_composites.finditer(req, re.IGNORECASE):
            operand = clean_operand(req[0:match.start(0) - last_start])
            expression += operand
            expression.append(match.group())

            req = req[match.end(0) - last_start::]
            last_start = match.end(0)

        expression += clean_operand(req)
        infix_expression = parse(expression)

    return parse_infix(infix_expression, courses_list).evaluate()

# ------ HELPER FUNCTIONS ------ #


def clean_operand(operand):
    if "," in operand or "units" in operand or "courses" in operand:
        return [operand.strip()]
    else:
        return operand.strip().replace("(", "( ").replace(")", " )").split()


def hasCourse(course, courses_list):
    return course.upper() in courses_list


def uoc_to_int(uoc):
    match_unit = r'(\d+) units'
    m = re.findall(match_unit, uoc, re.IGNORECASE)

    return int(m[0])/6


def course_intersection(course_listA, course_listB):
    course_listA = course_listA.replace("(", "").replace(")", "").split(", ")
    return [course for course in course_listA if course.upper() in course_listB]


def evaluate_req(condition, requirement, course_list):
    # Check for sufficient completion of required credits
    if condition == "completion":
        # Translate UOC to number of courses required
        requirement = uoc_to_int(requirement)
        return len(course_list) >= requirement
    else:
        condition = uoc_to_int(condition)

        if "courses" in requirement.split():
            req_type = req_level = re.findall(
                r'([a-z]{4}) courses', requirement, re.I)
            req_level = re.findall(r'level (\d+)', requirement, re.I)

            # Filters by level, or type of course
            if req_level:
                match_courses = re.compile(
                    req_type[0] + req_level[0] + r'\d{3}', re.I)
            else:
                match_courses = re.compile(
                    req_type[0] + r'\d{4}', re.I)

            filter_level = [
                course for course in course_list if match_courses.match(course)]

            return len(filter_level) >= condition
        else:
            return len(course_intersection(requirement, course_list)) >= int(condition)

# ------ PARSERS ------ #

# Parse and returns Infix notation of expression
# - Applies shunting yard algorithm


def parse(expression):
    operators = ["in", "or", "and", "(", ")"]
    course_queue = []
    composite_stack = []

    for el in expression:
        m = re.match(course_pattern, el, re.IGNORECASE)

        if el in operators and el == ")":
            last_op = None
            while last_op != "(":
                last_op = composite_stack.pop()
                if last_op != "(":
                    course_queue.append(last_op)
        elif el in operators:
            # Check precedence of operators
            if composite_stack and dict_precedence[el] < dict_precedence[composite_stack[-1]]:
                course_queue.append(composite_stack.pop())
            composite_stack.append(el)
        elif m:
            course_queue.append(m.group(0))
        else:
            course_queue.append(el)

    return course_queue + composite_stack

# Parses infix notation, converting expression to composite nodes


def parse_infix(expression_queue, courses_list):
    course_stack = []

    for expr in expression_queue:
        match_course = re.findall(r'[a-zA-Z]{4}\d{4}$', expr, re.IGNORECASE)

        if expr in composites:
            # If the expression is a boolean operator, create a composite node
            right_component = course_stack.pop()
            left_component = course_stack.pop()
            course_stack.append(createCompositeNode(
                expr, left_component, right_component, courses_list))
        elif any(word == "completion" for word in expr.split()):
            requirement, *condition = expr.split()
            course_stack.append(RequirementNode(
                requirement, ' '.join(condition), courses_list))
        elif match_course:
            course_stack.append(LeafNode(hasCourse(expr, courses_list)))
        else:
            course_stack.append(LeafNode(expr))

    return course_stack[0]


# ------ COMPOSITE PATTERN ------ #


class BooleanNode(ABC):
    @abstractmethod
    def evaluate(self):
        pass

    @abstractmethod
    def prettyPrint(self):
        pass


def createCompositeNode(type, left_component, right_component, courses_list):
    composite_type = {
        "and": AndComposite,
        "or": OrComposite,
        "in": InComposite,
    }

    return composite_type[type](left_component, right_component, courses_list)


class AndComposite(BooleanNode):
    def __init__(self, left, right, courses):
        self.left_component = left
        self.right_component = right

    def setLeftComponent(self, left):
        self.left_component = left

    def setRightComponent(self, right):
        self.left_component = right

    def evaluate(self):
        return self.left_component.evaluate() and self.right_component.evaluate()

    def prettyPrint(self):
        return (f"(AND {self.left_component.prettyPrint()} {self.right_component.prettyPrint()})")


class OrComposite(BooleanNode):
    def __init__(self, left, right, courses):
        self.left_component = left
        self.right_component = right

    def setLeftComponent(self, left):
        self.left_component = left

    def setRightComponent(self, right):
        self.left_component = right

    def evaluate(self):
        return self.left_component.evaluate() or self.right_component.evaluate()

    def prettyPrint(self):
        return f"(OR {self.left_component.prettyPrint()} {self.right_component.prettyPrint()})"


class InComposite(BooleanNode):
    def __init__(self, left, right, courses):
        self.left_component = left
        self.right_component = right
        self.course_list = courses

    def setLeftComponent(self, left):
        self.left_component = left

    def setRightComponent(self, right):
        self.left_component = right

    def evaluate(self):
        return evaluate_req(self.left_component.evaluate(), self.right_component.evaluate(), self.course_list)

    def prettyPrint(self):
        return f"(OR {self.left_component.prettyPrint()} {self.right_component.prettyPrint()})"


class RequirementNode(BooleanNode):
    def __init__(self, left, right, courses):
        self.condition = left
        self.requirement = right
        self.courses = courses

    def setLeftComponent(self, left):
        self.left_component = left

    def setRightComponent(self, right):
        self.left_component = right

    def evaluate(self):
        return evaluate_req(self.condition, self.requirement, self.courses)

    def prettyPrint(self):
        return f"(COMPLETION {self.condition} {self.requirement})"


class LeafNode(BooleanNode):
    def __init__(self, value):
        self.value = value

    def evaluate(self):
        return self.value

    def prettyPrint(self):
        return f"{self.value}"
