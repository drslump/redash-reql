import sys
from lark import Lark, Visitor, Tree


SQL_GRAMMAR = r'''
    // SQL syntax for SELECTs (based on sqlite3)
    // https://www.sqlite.org/lang_select.html
    //
    // Basic grammar is modeled from sqlite.
    //

    ?start                  : stmt (";"+ stmt?)*
                            | ";"*

    stmt                    : select_stmt
                            | reql_set_stmt


    compound_expr           : expr ("," expr)*
    ?expr                   : expr_or

    ?expr_or                : expr_and ( OR expr_and )*
    ?expr_and               : expr_not ( AND expr_not )*

    ?expr_not               : NOT+ expr_weird
                            | expr_weird

    ?expr_weird             : EXISTS "(" select_stmt ")" -> expr_exists
                            | expr_binary NOT? BETWEEN expr_binary AND expr_binary -> expr_between
                            | expr_binary NOT? IN expr_binary -> expr_in
                            | expr_binary ( IS NULL | NOTNULL | NOT NULL ) -> expr_null
                            | expr_binary NOT? ( LIKE | GLOB | REGEXP ) expr_binary [ ESCAPE expr_binary ] -> expr_search
                            | expr_binary
                            | expr_binary NOT? MATCH expr_binary [ ESCAPE expr_binary ] -> expr_search

    // TODO: shall we unwrap according to operator priority?
    ?expr_binary            : expr_unary (op_binary expr_unary)*

    ?expr_unary             : op_unary+ expr_func
                            | expr_unary COLLATE ident -> expr_collate
                            | expr_func
                            | expr_func ( "::" CNAME expr_parens? )+  -> expr_pgcast   // reql

    ?expr_func              : CASE expr? ( WHEN expr THEN expr )+ [ ELSE expr ] END -> expr_case
                            | CAST "(" expr AS type_ref ")" -> expr_cast
                            | ident_scoped expr_parens -> expr_call
                            | expr_parens

    ?expr_parens            : "(" [ DISTINCT? expr_arg ("," expr_arg)* | ASTERISK ] ")"
                            | atom

    expr_arg                : expr

    ?atom                   : literal
                            | parameter
                            | ident_scoped
                            | "(" select_stmt ")"  -> subquery
                            | "(" expr ")"


    type_ref                : CNAME [ "(" literal_number [ "," literal_number ] ")" ]

    op_binary               : "||" | "*" | "/" | "%" | "+" | "-"
                            | "<<" | ">>" | "&" | "|" | "<" | "<="
                            | ">" | ">=" | "=" | "==" | "!=" | "<>"
                            | IS | IS NOT

    op_unary                : "+" | "-" | "~"

    parameter               : PARAMETER  // TODO: support extended tcl syntax?
    alias                   : ident
                            | ident expr_parens?
                            | literal_string


    ?ident_scoped           : ident ("." ident)* ["." ASTERISK]
    ?compound_ident         : ident ("," ident)*
    ?compound_ident_scoped  : ident_scoped ("," ident_scoped)*


    ?literal                : literal_number
                            | literal_string
                            | NULL
                            | /x'([0-9A-Fa-f]+)'/  -> literal_blob
                            | CURRENT_TIME
                            | CURRENT_DATE
                            | CURRENT_TIMESTAMP

    literal_string          : SQUOTED
    literal_number          : NUMERIC

    ?table_or_subquery      : table_ref [ INDEXED BY ident | NOT INDEXED ]
                            | "(" select_stmt ")" [ AS? alias ] -> subquery
                            | "(" join ")"

    table_ref               : ident_scoped [ AS? alias ]
                            | ident_scoped "(" compound_expr? ")" [ AS? alias ]
                            | reql_expr

    cte                     : alias [ "(" compound_ident ")" ] AS "(" select_stmt ")"
                            | alias [ "(" compound_ident ")" ] AS reql_expr             -> reql_cte
                            | alias [ "(" compound_ident ")" ] AS "(" reql_expr ")"     -> reql_cte

    ?join                   : table_or_subquery ( op_join table_or_subquery join_constraint? )*

    join_constraint         : ON expr
                            | USING "(" compound_ident ")"

    op_join                 : ","
                            | NATURAL? [ LEFT OUTER? | INNER | CROSS ] JOIN

    column                  : ASTERISK
                            | expr [ AS? ident ]
                            | expr [ AS? (ident | literal_string) ]

    ?select_core            : values
                            | select

    values                  : VALUES ( expr_parens ("," expr_parens)* )

    select                  : SELECT select_mod? column ("," column)* from? where? group? having? order?

    select_mod              : DISTINCT | ALL

    from                    : FROM join
    where                   : WHERE expr
    group                   : GROUP BY compound_expr
    having                  : HAVING expr

    ?compound_select        : select_core ( op_compound select_core )*
    op_compound             : UNION ALL?
                            | INTERSECT
                            | EXCEPT

    with                    : WITH RECURSIVE? cte ("," cte)*

    order                   : ORDER BY ordering_term ("," ordering_term)*
    ordering_term           : expr [ ASC | DESC ]

    limit                   : LIMIT expr [ ("OFFSET"i|",") expr ]

    select_stmt             : with? compound_select order? limit?

    ident                   : CNAME | DQUOTED
                            | /\[([^\]].+?)\]/    // Access style [quotes]


    //
    // ReQL constructs
    //
    /////////////////////////////////////////////////////////

    reql_expr       : CNAME reql_params reql_mapper*
    reql_params     : "[" [ reql_param (","? reql_param)* ] "]" | reql_block
    ?reql_param     : reql_pair | ident | literal | parameter
    reql_pair       : CNAME ":" (ident | literal | parameter | reql_block)
    reql_block      : /\[:([\s\S]*?):\]/   -> reql_block
                    | /\[=([\s\S]*?)=\]/   -> reql_block_verbatim
                    | /\[<([\s\S]*?)>\]/   -> reql_block_folded
    reql_mapper     : "::" CNAME reql_params?

    reql_set_stmt   : "SET"i CNAME "=" (literal | CNAME)


    %import common.CNAME
    %import common.NEWLINE
    %ignore NEWLINE
    %import common.WS
    %ignore WS

    COMMENT                 : "--" /[^\n]+?/? NEWLINE
                            | "/*" /(.|\n)*?/ "*/"
    %ignore COMMENT

    PARAMETER               : ("$" | ":") CNAME

    SQUOTED                 : "'" ( "''" | NEWLINE | /[^']+/ )* "'"
    DQUOTED                 : "\"" ( "\"\"" | /[^"]+/ )* "\""

    NUMERIC                 : ( DIGIT+ [ "." DIGIT+ ] | "." DIGIT+ ) [ ("e"|"E") [ "+"|"-" ] DIGIT+ ]
                            | ("0x"|"0X") HEXDIGIT+
    DIGIT                   : "0".."9"
    HEXDIGIT                : "0".."9" | "A".."F" | "a".."f"

    ALL                     : "ALL"i
    AND                     : "AND"i
    AS                      : "AS"i
    ASC                     : "ASC"i
    ASTERISK                : "*"
    BETWEEN                 : "BETWEEN"i
    BY                      : "BY"i
    CASE                    : "CASE"i
    CAST                    : "CAST"i
    COLLATE                 : "COLLATE"i
    CROSS                   : "CROSS"i
    CURRENT_DATE            : "CURRENT_DATE"i
    CURRENT_TIME            : "CURRENT_TIME"i
    CURRENT_TIMESTAMP       : "CURRENT_TIMESTAMP"i
    DESC                    : "DESC"i
    DISTINCT                : "DISTINCT"i
    ELSE                    : "ELSE"i
    END                     : "END"i
    ESCAPE                  : "ESCAPE"i
    EXCEPT                  : "EXCEPT"i
    EXISTS                  : "EXISTS"i
    FROM                    : "FROM"i
    GLOB                    : "GLOB"i
    GROUP                   : "GROUP"i
    HAVING                  : "HAVING"i
    IGNORE                  : "IGNORE"i
    IN                      : "IN"i
    INDEXED                 : "INDEXED"i
    INNER                   : "INNER"i
    INTERSECT               : "INTERSECT"i
    IS                      : "IS"i
    ISNULL                  : "ISNULL"i
    JOIN                    : "JOIN"i
    LEFT                    : "LEFT"i
    LIKE                    : "LIKE"i
    LIMIT                   : "LIMIT"i
    MATCH                   : "MATCH"i
    NATURAL                 : "NATURAL"i
    NOT                     : "NOT"i
    NOTNULL                 : "NOTNULL"i
    NULL                    : "NULL"i
    ON                      : "ON"i
    OR                      : "OR"i
    ORDER                   : "ORDER"i
    OUTER                   : "OUTER"i
    RECURSIVE               : "RECURSIVE"i
    REGEXP                  : "REGEXP"i
    SELECT                  : "SELECT"i
    THEN                    : "THEN"i
    UNION                   : "UNION"i
    USING                   : "USING"i
    VALUES                  : "VALUES"i
    WHEN                    : "WHEN"i
    WHERE                   : "WHERE"i
    WITH                    : "WITH"i
'''


class ReqlParser(object):

    def __init__(self, transformer=None, postlex=None):
        self.lark = Lark(
            SQL_GRAMMAR, start='start', parser='lalr',
            transformer=transformer, postlex=postlex)

    def parse(self, code, transformer=None):
        tree = self.lark.parse(code)
        if transformer:
            transformer.transform(tree)
        return tree
