# Copyright (c) 2016 by Gilbert Ramirez <gramirez@a10networks.com>
"""
Show individual records, using logical syntax similar to the "find" command
"""
from instmakelib import instmake_log as LOG
import sys
import re
import os

description = "Find records using a syntax similar to 'find'"

def usage():
    print "find:", description
    print "\t[(] [FIELD] regex [)] [-o|-a] ..."
    print
    print "\tFIELD: --cmdline, --tool, --target, --cwd, --retval"


TOK_REGEX = "regular expression"
TOK_TOOL = "--tool"
TOK_TARGET = "--target"
TOK_CWD = "--cwd"
TOK_RETVAL = "--retval"
TOK_CMDLINE = "--cmdline"

FIELDNAME_TOKENS = (TOK_TOOL, TOK_TARGET, TOK_CWD, TOK_RETVAL, TOK_CMDLINE)

TOK_AND = "-a"
TOK_OR = "-o"
TOK_LPAREN = "("
TOK_RPAREN = ")"

class Token:
    def __init__(self, type_, value):
        self.type_ = type_
        self.value = value

    def Type(self):
        return self.type_

    def Value(self):
        return self.value

    def SetValue(self, value):
        if self.value is not None:
            raise ValueError("%s has value %s; cannot set to %s" % (
                self, self.value, value))
        self.value = value

    def __str__(self):
        return "<Token %s/%s>" % (self.type_, self.value)

class TokenStream:
    """Records tokens coming in from the CLI processor"""
    def __init__(self):
        self.tokens = []

    def __len__(self):
        return len(self.tokens)

    def Append(self, token):
        """Will raise ValueError if the token type is not
        valid in terms of the sequence of other tokens"""
        assert isinstance(token, Token)

        if len(self.tokens) == 0:
            if token.Type() in (TOK_AND, TOK_OR):
                raise ValueError("%s cannot be the first option" % token.Type())
        else:
            # If this doesn't raise an exception, then we can continue
            self._CheckNewToken(token)

        self.tokens.append(token)

    def _CheckNewToken(self, token):
        last_token = self.tokens[-1]
        if last_token.Type() in FIELDNAME_TOKENS:
            if token.Type() != TOK_REGEX:
                raise ValueError("After %s, a regex is required, not %s" % (
                    last_token.Type(), token.Type()))
        elif last_token.Type() in (TOK_AND, TOK_OR, TOK_LPAREN):
            if token.Type() not in FIELDNAME_TOKENS + (TOK_LPAREN,):
                raise ValueError("After %s, a field option is required, not %s" % (
                    last_token.Type(), token.Type()))
        elif last_token.Type() == TOK_REGEX:
            if token.Type() not in (TOK_AND, TOK_OR, TOK_RPAREN) + FIELDNAME_TOKENS:
                raise ValueError("After a regex, %s is not allowed" % (
                    token.Type()))
        elif last_token.Type() == TOK_RPAREN:
            if token.Type() not in (TOK_AND, TOK_OR, TOK_RPAREN) + FIELDNAME_TOKENS:
                raise ValueError("After a ), %s is not allowed" % (
                    token.Type()))

    def CheckFinal(self):
        last_token = self.tokens[-1]
        if last_token.Type() not in (TOK_REGEX, TOK_RPAREN):
            raise ValueError("%s cannot be the final option" % (last_token.Type(),))

    def Parse(self):
        """Parse the token stream, and return a SyntaxTreeNode, which is the
        root node of the overall syntax tree"""

        # Combine a fieldname token with its TOK_REGEX value
        new_token_stream = []
        for token in self.tokens:
            self._SetFieldnameValues(new_token_stream, token)

        # Parse into a syntax tee
        node_stack = []
        for token in new_token_stream:
            self._Parse(node_stack, token)

        if len(node_stack) != 1:
            print >> sys.stderr, "Nodes:"
            for node in node_stack:
                print >> sys.stderr, "  ", node
            raise ValueError("Expected 1 node after parsing")

        return node_stack[0]

    def _SetFieldnameValues(self, new_token_stream, token):
        if len(new_token_stream) == 0:
            new_token_stream.append(token)

        elif token.Type() == TOK_REGEX:
            last_token = new_token_stream[-1]
            assert last_token.Type() in FIELDNAME_TOKENS
            last_token.SetValue(token.Value())

        else:
            new_token_stream.append(token)


    def _Parse(self, stack, token):
        assert token.Type() != TOK_REGEX
        node = Node(token)

        if len(stack) == 0:
            stack.append(node)
            return

        last_node = stack[-1]
        if token.Type() in (TOK_AND, TOK_OR):
            node.SetLeft(last_node)
            stack[-1] = node

        elif token.Type() == TOK_LPAREN:
            stack.append(node)

        elif token.Type() in FIELDNAME_TOKENS:
            last_node = stack[-1]
            if last_node.Type() in (TOK_AND, TOK_OR):
                last_node.SetRight(node)
            else:
                stack.append(node)

        elif token.Type() == TOK_RPAREN:
            self._CloseParens(stack)

        else:
            raise ValueError("Unexpected token %s" % token)


    def _CloseParens(self, stack):
        assert len(stack) >= 2
        last_node = stack[-1]
        lparen_node = stack[-2]
        assert lparen_node.Type() == TOK_LPAREN
        stack[-2] = last_node
        del stack[-1]

        if len(stack) == 1:
            return

        # AND(X, None) Y -> AND(X, Y)
        # OR(X, None) Y -> OR(X, Y)
        prev_node = stack[-2]
        if prev_node.Type() in (TOK_AND, TOK_OR):
            prev_node.SetRight(last_node)
            del stack[-1]


class Node:
    """One node in a syntax tree."""
    def __init__(self, token):
        assert isinstance(token, Token)
        self.token = token
        self.left = None
        self.right = None

    def Type(self):
        return self.token.Type()

    def __str__(self):
        return "<Node %s>" % (self.token)

    def Dump(self, indent=0, tag=""):
        spaces = "  " * indent + tag
        print "%s%s%s" % (spaces, tag, self.token)
        if self.left is not None:
            self.left.Dump(indent + 1, "L:")
        if self.right is not None:
            self.right.Dump(indent + 1, "R:")

    def SetLeft(self, node):
        assert isinstance(node, Node)
        if self.left is not None:
            raise ValueError("%s already has left %s, can't set to %s" % (
                self, self.left, node))
        self.left = node

    def SetRight(self, node):
        assert isinstance(node, Node)
        if self.right is not None:
            raise ValueError("%s already has right %s, can't set to %s" % (
                self, self.right, node))
        self.right = node

    def Apply(self, rec):
        """Apply the syntax node logic to a record.
        Returns True/False, if the record matches the syntax node or not."""

        if self.token.Type() == TOK_AND:
            assert self.left is not None
            assert self.right is not None
            if not self.left.Apply(rec):
                # Short-circuit
                return False
            return self.right.Apply(rec)

        elif self.token.Type() == TOK_OR:
            assert self.left is not None
            assert self.right is not None
            if self.left.Apply(rec):
                # Short-circuit
                return True
            return self.right.Apply(rec)

        elif self.token.Type() in FIELDNAME_TOKENS:
            if self.token.Type() == TOK_TOOL:
                field = rec.tool
            elif self.token.Type() == TOK_TARGET:
                # Can be None
                field = rec.make_target or ""
            elif self.token.Type() == TOK_CWD:
                field = rec.cwd
            elif self.token.Type() == TOK_RETVAL:
                field = str(rec.retval)
            elif self.token.Type() == TOK_CMDLINE:
                field = rec.cmdline
            else:
                raise ValueError("Unexpected field name %s" % self.token.Type())
            assert self.token.Value() is not None
            m = self.token.Value().search(field)
            return m is not None

        else:
            raise ValueError("Unexpected token type: %s" % self.token.Type())


def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'find' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    try:
        token_stream = ParseCLI(args)
        if len(token_stream) == 0:
            sys.exit("No search options given")
        token_stream.CheckFinal()
    except ValueError as e:
        sys.exit(e)

    syntax_tree = token_stream.Parse()
#    syntax_tree.Dump()

    # Open the log file
    log = LOG.LogFile(log_file_name)

    # Read through the records
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        if syntax_tree.Apply(rec):
            rec.Print()



def ParseCLI(args):
    STATE_ANY = 0
    STATE_REGEX = 1
    state = STATE_ANY

    token_stream = TokenStream()

    arg_num = 0
    for arg in args:
        arg_num += 1
        if state == STATE_ANY:
            if arg in (TOK_AND, TOK_OR, TOK_LPAREN, TOK_RPAREN):
                token_stream.Append(Token(arg, None))
                continue
            elif arg in FIELDNAME_TOKENS:
                token_stream.Append(Token(arg, None))
                state = STATE_REGEX
                continue
            else:
                raise ValueError("%s unexpected as argument #%d" % (
                    arg, arg_num))

        elif state == STATE_REGEX:
            try:
                regex = re.compile(arg)
            except re.error as e:
                raise ValueError("Incorrect regex %s: %s" % (arg, e))
            token_stream.Append(Token(TOK_REGEX, regex))
            state = STATE_ANY
            continue

        else:
            assert False, "State %d unexpected" % (state,)

    return token_stream


