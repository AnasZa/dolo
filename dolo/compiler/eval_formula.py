from ast import *
# from dolo.compiler.function_compiler_ast import std_date_symbol, to_source
from dolang import normalize, stringify, to_source
from dolo.compiler.misc import CalibrationDict


def eval_formula(expr, dataframe=None, context=None):
    '''
    expr: string
        Symbolic expression to evaluate.
        Example: `k(1)-delta*k-i`
    table: (optional) pandas dataframe
        Each column is a time series, which can be indexed with dolo notations.
    context: dict or CalibrationDict
    '''

    if context is None:
        dd = {}  # context dictionary
    elif isinstance(context, CalibrationDict):
        dd = context.flat.copy()
    else:
        dd = context.copy()

    # compat since normalize form for parameters doesn't match calib dict.
    for k in [*dd.keys()]:
        dd[stringify(k)] = dd[k]

    from numpy import log, exp
    dd['log'] = log
    dd['exp'] = exp

    if dataframe is not None:

        import pandas as pd
        tvariables = dataframe.columns
        for k in tvariables:
            if k in dd:
                dd[k+'_ss'] = dd[k]  # steady-state value
            dd[stringify((k, 0))] = dataframe[k]
            for h in range(1, 3):  # maximum number of lags
                dd[stringify((k, -h))] = dataframe[k].shift(h)
                dd[stringify((k, h))] = dataframe[k].shift(-h)
        dd['t'] = pd.Series(dataframe.index, index=dataframe.index)

        import ast
        expr_ast = ast.parse(expr).body[0].value
        # nexpr = StandardizeDatesSimple(tvariables).visit(expr_ast)
        print(tvariables)
        nexpr = normalize(expr_ast, variables=tvariables)

        expr = to_source(nexpr)

    res = eval(expr, dd)

    return res

class StandardizeDatesSimple(NodeTransformer):

    # replaces calls to variables by time subscripts

    def __init__(self, variables):

        self.variables = variables  # list of variables

    def visit_Name(self, node):

        name = node.id
        newname = normalize((name, 0))
        if name in self.variables:
            expr = Name(newname, Load())
            return expr
        else:
            return node

    def visit_Call(self, node):

        name = node.func.id
        args = node.args[0]

        if name in self.variables:
            if isinstance(args, UnaryOp):
                # we have s(+1)
                if (isinstance(args.op, UAdd)):
                    args = args.operand
                    date = args.n
                elif (isinstance(args.op, USub)):
                    args = args.operand
                    date = -args.n
                else:
                    raise Exception("Unrecognized subscript.")
            else:
                date = args.n
            newname = std_date_symbol(name, date)
            if newname is not None:
                return Name(newname, Load())

        else:

            # , keywords=node.keywords, starargs=node.starargs, kwargs=node.kwargs)
            return Call(func=node.func, args=[self.visit(e) for e in node.args], keywords=[])
