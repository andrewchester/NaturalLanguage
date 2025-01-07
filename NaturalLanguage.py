import os
import re
import sys

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def collapse(L):
    collapsed = []

    for item in L:
        if type(item) == list:
            collapsed += [*collapse(item)]
        else:
            collapsed.append(item)

    return collapsed

class Interpreter:
    def __init__(self):
        self.variableTable = {}

        self.loadingFunction = False
        self.activeFunction = None

        self.inFunction = False
        self.returnValue = None

        self.operators = {
            'is': self.assignment,
            'Display': self.display,
            '+': self.math,
            '-': self.math,
            '*': self.math,
            '/': self.math,
            '%': self.math,
            '^': self.math,
            'at': self.indexList,
            ',': None, # list construction is handled as a special case during statement execution
            'Run': self.runFunction,
            'with': self.parameterConstruction,
            'return': self.exitFunction
        }

        self.conditional = "If"

        self.relations = {
            'equals': self.equality
        }

        self.precedence = {
            'return': 0,
            'is': 1,
            'Display': 2,
            ',': 3,
            '+': 4,
            '-': 5,
            '*': 5,
            '/': 5,
            '%': 5,
            '^': 6,
            'Run': 7,
            'with': 8,
            'at': 9
        }

        self.arithmetic = {
            '+': lambda a, b : a + b,
            '-': lambda a, b : a - b,
            '*': lambda a, b: a * b,
            '/': lambda a, b: a / b,
            '%': lambda a, b: int(a) % int(b),
            '^': lambda a, b: a ** b
        }

        self.filler = ['a', 'an']

    def assignment(self, tokens, **kwargs):
        if len(tokens) < 2:
            raise RuntimeError("Assignment error")

        if type(tokens[1]) == dict and tokens[1]['type'] == 'function':
            if self.loadingFunction:
                self.activeFunction = tokens[0]
            self.variableTable[tokens[0]] = tokens[1]
        elif type(tokens[1]) != list and is_number(tokens[1]):
            self.variableTable[tokens[0]] = float(tokens[1])
        else:
            self.variableTable[tokens[0]] = tokens[1]

        return []

    def display(self, tokens, **kwargs):
        if len(tokens) == 0:
            print()

        for token in tokens:
            print(token, end = ' ')

        print()

        return []

    def evalLiteral(self, literal):
        if type(literal) == list:
            return literal
        if literal in self.variableTable:
            if type(self.variableTable[literal]) == dict:
                func = self.variableTable[literal]
                func['name'] = literal
                return func
            return self.variableTable[literal]
        if is_number(literal):
            return float(literal)
        if literal == 'True':
            return True
        if literal == 'False':
            return False
        return literal

    def indexList(self, tokens, **kwargs):
        if len(tokens) != 2:
            raise SyntaxError("Index requires a list and an index")
        
        if not is_number(tokens[1]):
            raise TypeError("Index must be a number")

        if type(tokens[0]) != list:
            raise TypeError("You can only index a list")

        return [tokens[0][int(tokens[1]-1)]]

    def math(self, tokens, **kwargs):
        if len(tokens) != 2:
            raise RuntimeError("Input error")

        mathematicalOperator = kwargs.get('mathOperator', None)

        if mathematicalOperator is None:
            raise RuntimeError("Error parsing mathematical statement")

        left, right = tokens[0], tokens[1]

        if type(left) == str or type(right) == str:
            raise TypeError("Invalid type for mathematical operation")

        if type(left) == list:
            result = []
            for token in left:
                result.append(*self.math(tokens = [token, tokens[1]], mathOperator = mathematicalOperator))
            return [result]

        if type(right) == list:
            result = []
            for token in right:
                result.append(*self.math(tokens = [tokens[0], token], mathOperator = mathematicalOperator))
            return [result]
        
        return [self.arithmetic[mathematicalOperator](left, right)]

    def runFunction(self, tokens, **kwargs):
        func = tokens[0]

        if len(func['params']) != len(func['values']):
            raise RuntimeError(f'parameters are:{func['params']}')

        backupVariables = self.variableTable.copy()
    
        for param, value in zip(func['params'], func['values']):
            self.variableTable[param] = value

        self.inFunction = True

        for statement in func['execute']:
            if self.returnValue != None:
                break

            if statement[0] == self.conditional:
                self.executeConditional(statement[1:])
            else:
                self.executeStatement(statement)

        self.variableTable = backupVariables

        result = [self.returnValue] if self.returnValue is not None else []
        
        self.returnValue = None
        self.inFunction = False

        return result

    def exitFunction(self, tokens, **kwargs):
        if len(tokens) != 1:
            raise RuntimeError("Only one value can be returned from a function")
        
        if not self.inFunction:
            raise RuntimeError("You can only return from inside a function")

        self.returnValue = tokens[0]

        return []

    def parameterConstruction(self, tokens, **kwargs):
        if len(tokens) <= 1:
            raise SyntaxError("Function calls or definitions must specify a function to pair parameters with.")

        if tokens[0] == 'function':
            newFunction = {
                'type': 'function',
                'execute': [],
                'params': tokens[1:]
            }

            self.loadingFunction = True

            return [newFunction]

        func = tokens[0]
        if type(func) == dict and func['type'] == 'function':
            func['values'] = tokens[1] if type(tokens[1]) == list else [tokens[1]]
            return [func]
        else:
            raise RuntimeError(f'{tokens[0]} is not a function')

    def executeStatement(self, tokens):
        tokens = [token for token in tokens if token not in self.filler]
        precedentOperation = [None, float('inf')]

        for operator, _ in self.operators.items():
            if operator == ',':
                for token in tokens:
                    if token[-1] == operator and self.precedence[operator] < precedentOperation[1]:
                        precedentOperation = [operator, self.precedence[operator]]
            elif operator in tokens and self.precedence[operator] < precedentOperation[1]:
                precedentOperation = [operator, self.precedence[operator]]

        if len(tokens) == 1 and tokens[0] in self.operators:
            raise SyntaxError("Operator syntax error")
        if len(tokens) == 1:
            return [self.evalLiteral(tokens[0])]
        if precedentOperation[0] is None:
            raise SyntaxError("Each statement must contain an operation")
            
        operator, _ = precedentOperation
        
        if operator == ',':
            result = []
            sequence = []

            while tokens:
                token = tokens.pop(0)
                if token[-1] == operator:
                    sequence.append(token[:-1])
                    result.append(*self.executeStatement(sequence))
                    sequence = []
                else:
                    sequence.append(token)
            
            if sequence:
                result.append(*self.executeStatement(sequence))

            return [result]
        
        operatorIdx = tokens.index(precedentOperation[0])
        
        if operator != 'is':
            leftResult = self.executeStatement(tokens[:operatorIdx]) if tokens[:operatorIdx] != [] else []
        else:
            leftResult = tokens[:operatorIdx]
        rightResult = self.executeStatement(tokens[operatorIdx+1:]) if tokens[operatorIdx+1:] != [] else []

        return self.operators[operator](tokens = [*leftResult, *rightResult], mathOperator=operator)

    def equality(self, tokens):
        if len(tokens) != 2:
            raise RuntimeError("Conditional error")

        leftValue = tokens[0]
        rightValue = tokens[1]

        if tokens[0] in self.variableTable:
            leftValue = self.variableTable[tokens[0]]
        elif is_number(tokens[0]):
            leftValue = float(tokens[0])
        if tokens[1] in self.variableTable:
            rightValue = self.variableTable[tokens[1]]
        elif is_number(tokens[1]):
            rightValue = float(tokens[1])

        return leftValue == rightValue

    def executeConditional(self, tokens):
        delimiterIdx = None
        for i, token in enumerate(tokens):
            if ',' in token and delimiterIdx is not None:
                raise SyntaxError("A conditional may only have one ','")
            if token[-1] == ',':
                delimiterIdx = i
                

        tokens[delimiterIdx] = tokens[delimiterIdx][:-1]
        
        if delimiterIdx is None:
            raise SyntaxError("Conditionals must contain a condition with an equivalence statement, then a ',', followed by a statement")
        
        equivalenceStatement = tokens[:delimiterIdx+1]
        statement = tokens[delimiterIdx+1:]

        if equivalenceStatement == []:
            raise SyntaxError("A conditional must have a condition")
        if statement == []:
            raise SyntaxError("A conditional must have a statement to execute")
        
        relation = None

        for token in equivalenceStatement:
            if token in self.relations and relation is None:
                relation = token
            elif token in self.relations and relation is not None:
                raise SyntaxError("A conditional must have only one relation")
        
        if relation is None:
            raise SyntaxError("A conditional must have a relation")

        relatorIdx = tokens.index(relation)
        leftTokens = tokens[:relatorIdx]
        rightTokens = tokens[relatorIdx+1:delimiterIdx+1]

        if self.relations[relation]([*self.executeStatement(leftTokens), *self.executeStatement(rightTokens)]):
            self.executeStatement(statement)

    def parseLine(self, line):
        if line[-1] != '.':
            raise SyntaxError("Each line must end with a '.'")

        tokens = line[:-1].split(' ')

        if tokens[0] == '' and self.loadingFunction:
            tokens = tokens[1:]
            self.variableTable[self.activeFunction]['execute'].append(tokens)
            return

        if tokens[0] != '' and self.loadingFunction:
            self.loadingFunction = False
            self.activeFunction = None
        
        if tokens[0] == '' and not self.loadingFunction:
            raise SyntaxError("Indentation is only used in code blocks.")
            
        if tokens[0] == self.conditional:
            self.executeConditional(tokens[1:])
        else:
            self.executeStatement(tokens)

    def loadSource(self, path):
        with open(path, 'r') as f:
            for i, line in enumerate(f.readlines()):
                if line.rstrip() == '' or line[:2] == '//':
                    continue

                try:
                    self.parseLine(line.rstrip())
                except SyntaxError as e:
                    print(f'Syntax error on line {i+1}:', e)
                except TypeError as e:
                    print(f'Type Error on line {i+1}:', e)
                except RuntimeError as e:
                    print(f'Runtime error on line {i+1}:', e)
                except Exception as e:
                    print("Unknown Error occured:",e)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Please specify source file.")
        exit()

    path = sys.argv[1]

    if path[-3:] != '.nl':
        print("Please provide a NaturalLanguage .nl file.")

    I = Interpreter()
    I.loadSource(path)