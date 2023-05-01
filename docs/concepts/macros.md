# Macros

SQL is a static language. It does not have features like variables or control flow logic (if-then) that allow SQL commands to behave differently in different situations.

However, data pipelines are dynamic and need different behavior depending on context. SQL is made dynamic with *macros*. 

SQLMesh supports two macro systems: SQLMesh macros and the [Jinja](https://jinja.palletsprojects.com/en/3.1.x/) templating system. 

This page describes how to use macros to build dynamic data pipelines with SQLMesh.

## Variables
Macro systems are based on string substitution. The macro system scans code files, identifies special characters that signify macro content, and replaces the macro elements with other text. 

The most common use case for macros is variable substitution. For example, you might have a SQL query that filters by date in the `WHERE` clause. 

Instead of manually changing the date each time the model is run, you can use a macro variable to make the date dynamic. With the dynamic approach the date changes automatically based on when the query is run. 

Consider this query that filters for rows where column `my_date` is after '2023-01-01':

```sql linenums="1"
SELECT *
FROM table
WHERE my_date > '2023-01-01'
```

To make this query's date dynamic you could use the predefined SQLMesh macro variable `@latest_ds`: 

```sql linenums="1"
SELECT *
FROM table
WHERE my_date > @latest_ds
```

The `@` symbol tells SQLMesh that `@latest_ds` is a macro variable that require substitution before the SQL is executed. 

The macro variable `@latest_ds` is predefined, so its value will be automatically set by SQLMesh based on when the model was last executed. If the model was last run on January 1, 2023 the resulting query would be:

```sql linenums="1"
SELECT *
FROM table
WHERE my_date > '2023-01-01'
```

This example used one of SQLMesh's predefined variables, but you can also create your own custom macro variables.

We describe SQLMesh's predefined variables next and custom macro variables in the subsequent [User-defined Variables](#user-defined-variables) section.

### Predefined Variables
SQLMesh comes with predefined variables that can be used in your queries. They are automatically set by the SQLMesh runtime. 

These variables are related to time and are comprised of a combination of prefixes (start, end, latest) and postfixes (date, ds, ts, epoch, millis).

Prefixes:

* start - The inclusive starting interval of a model run.
* end - The inclusive end interval of a model run.
* latest - The most recent date SQLMesh ran the model.

Postfixes:

* date - A python date object that converts into a native SQL Date.
* ds - A date string with the format: '%Y-%m-%d'
* ts - An ISO 8601 datetime formatted string: '%Y-%m-%d %H:%M:%S'.
* epoch - An integer representing seconds since epoch.
* millis - An integer representing milliseconds since epoch.

All predefined macro variables:

* date
    * @start_date
    * @end_date
    * @latest_date

* ds
    * @start_ds
    * @end_ds
    * @latest_ds

* ts
    * @start_ts
    * @end_ts
    * @latest_ts

* epoch
    * @start_epoch
    * @end_epoch
    * @latest_epoch

* millis
    * @start_millis
    * @end_millis
    * @latest_millis

#TODO: python date objects
#TODO: epoch values

### User-defined variables

Define your own macro variables with the `@DEF` macro operator. For example, you could set the macro variable `macro_var` to the value `1` with:

```sql linenums="1"
@DEF(macro_var, 1);
```

SQLMesh has three basic requirements for using the `@DEF` operator:
1. The `MODEL` DDL statement must end with a semi-colon `;`
2. All `@DEF` uses must come after the `MODEL` DDL statement and before the SQL code
3. Each `@DEF` use must end with a semi-colon `;`

For example, consider the following model `sqlmesh_example.full_model` from the SQLMesh quickstart guide:

```sql linenums="1"
MODEL (
  name sqlmesh_example.full_model,
  kind FULL,
  cron '@daily',
  audits [assert_positive_order_ids],
);

SELECT
  item_id,
  count(distinct id) AS num_orders,
FROM
    sqlmesh_example.incremental_model
GROUP BY item_id
```

This model could be extended to use a user-defined macro variable to filter the query results based on `item_size` like this:

```sql linenums="1"
MODEL (
  name sqlmesh_example.full_model,
  kind FULL,
  cron '@daily',
  audits [assert_positive_order_ids],
); -- NOTE: semi-colon at end of MODEL DDL statement

@DEF(size, 1); -- NOTE: semi-colon at end of @DEF operator

SELECT
  item_id,
  count(distinct id) AS num_orders,
FROM
    sqlmesh_example.incremental_model
WHERE
    item_size > @size
GROUP BY item_id
```

This example defines the macro variable `size` with `@DEF(size, 1)`. When the model is run, SQLMesh will substitute in the number `1` where `@size` appears in the `WHERE` clause.

TODO: describe quoting behavior when quotes included/excluded in @DEF

# SQLMesh macro operators

SQLMesh's macro system has multiple operators that allow different forms of dynamism in models.


## SQL clause operators

SQLMesh's macro system has six operators that correspond to different clauses in SQL syntax. They are:

- `@WITH`: common table expression `WITH` clause
- `@JOIN`: table `JOIN` clause(s)
- `@WHERE`: filtering `WHERE` clause
- `@GROUP_BY`: grouping `GROUP BY` clause
- `@HAVING`: group by filtering `HAVING` clause
- `@ORDER_BY`: ordering `ORDER BY` clause

Each of these operators is used to dynamically add the code for its corresponding clause to a model's SQL query.

### How SQL clause operators work
The SQL clause operators take a single argument that determines whether the clause is generated. 

If the argument is True the clause code is generated, if False the code is not. The argument's truth is determined by executing its contents as Python code. 

As an example, let's revisit the example model from the [User-defined Variables](#user-defined-variables) section above. 

As written, the model will always include the `WHERE` clause. We could make its presence dynamic by using the `@WHERE` macro operator:

```sql linenums="1"
MODEL (
  name sqlmesh_example.full_model,
  kind FULL,
  cron '@daily',
  audits [assert_positive_order_ids],
);

@DEF(size, 1);

SELECT
  item_id,
  count(distinct id) AS num_orders,
FROM
    sqlmesh_example.incremental_model
@WHERE(True) item_id > @size
GROUP BY item_id
```

The `@WHERE` argument is set to `True`, so the WHERE code is included in the rendered model:

```sql linenums="1"
SELECT
  item_id,
  count(distinct id) AS num_orders,
FROM
    sqlmesh_example.incremental_model
WHERE item_id > 1
GROUP BY item_id
```

If the `@WHERE` argument were instead set to `False` the `WHERE` clause would be omitted from the query.

These operators aren't too useful if the argument's value is hard-coded. Instead, the argument can consist of code executable by Python. 

For example, the `WHERE` clause will be included in this query because 1 is in fact less than 2:

```sql linenums="1"
MODEL (
  name sqlmesh_example.full_model,
  kind FULL,
  cron '@daily',
  audits [assert_positive_order_ids],
);

@DEF(size, 1);

SELECT
  item_id,
  count(distinct id) AS num_orders,
FROM
    sqlmesh_example.incremental_model
@WHERE(1 < 2) item_id > @size
GROUP BY item_id
```

The operator's argument code can include macro variables. 

In this example, the two numbers being compared are defined as macro variables instead of being hard-coded:

```sql linenums="1"
MODEL (
  name sqlmesh_example.full_model,
  kind FULL,
  cron '@daily',
  audits [assert_positive_order_ids],
);

@DEF(left_number, 1);
@DEF(right_number, 2);
@DEF(size, 1);

SELECT
  item_id,
  count(distinct id) AS num_orders,
FROM
    sqlmesh_example.incremental_model
@WHERE(@left_number < @right_number) item_id > @size
GROUP BY item_id
```

### SQL clause operator examples

This section provides brief examples of each SQL clause operator's usage.

The examples use variants of this simple select statement:

```sql linenums="1"
SELECT *
FROM all_cities
```

#### `@WITH` operator

```sql linenums="1"
@WITH(True) all_cities as (select * from city) 
select *
FROM all_cities
```

renders to

```sql linenums="1"
WITH all_cities as (select * from city) 
select *
FROM all_cities
```

#### `@JOIN` operator

```sql linenums="1"
select *
FROM all_cities
LEFT OUTER @JOIN(True) country 
    ON city.country = country.name
```

renders to

```sql linenums="1"
select *
FROM all_cities
LEFT OUTER JOIN country 
    ON city.country = country.name
```

The `@JOIN` operator recognizes that `LEFT OUTER` is a component of the `JOIN` specification and will omit it if the argument evaluates to False.

#### `@WHERE` operator

```sql linenums="1"
SELECT *
FROM all_cities
@WHERE(True) city_name = 'Toronto'
```

renders to

```sql linenums="1"
SELECT *
FROM all_cities
WHERE city_name = 'Toronto'
```

#### `@GROUP_BY` operator

```sql linenums="1"
SELECT *
FROM all_cities
@GROUP_BY(True) city_id
```

renders to

```sql linenums="1"
SELECT *
FROM all_cities
GROUP BY city_id
```

#### `@HAVING` operator

```sql linenums="1"
SELECT 
count(city_pop) as population
FROM all_cities
GROUP BY city_id
@HAVING(True) population > 1000
```

renders to

```sql linenums="1"
SELECT 
count(city_pop) as population
FROM all_cities
GROUP BY city_id
HAVING population > 1000
```

#### `@ORDER_BY` operator

```sql linenums="1"
SELECT *
FROM all_cities
@ORDER_BY(True) city_pop
```

renders to

```sql linenums="1"
SELECT *
FROM all_cities
ORDER BY city_pop
```

### Functional operators
@EACH
@REDUCE
@FILTER

### Meta Operators
@SQL
@''

## User-defined macro functions


## Jinja
[Jinja](https://jinja.palletsprojects.com/en/3.1.x/) is a popular templating tool for creating dynamic SQL and is supported by SQLMesh, but there are some drawbacks which lead for us to create our own macro system.

* Jinja is not valid SQL and not parseable.
```sql linenums="1"
-- templating allows for arbitrary string replacements which is not feasible to parse
SE{{ 'lect' }} x {{ 'AS ' + var }}
FROM {{ 'table CROSS JOIN z' }}
```

* Jinja is verbose and difficult to debug.
```sql linenums="1"
TBD example with multiple for loops with trailing or leading comma
```
* No concepts of types. Easy to miss quotes.

```sql linenums="1"
SELECT *
FROM table
WHERE ds BETWEEN '{{ start_ds }}' and '{{ end_ds }}'  -- quotes are needed
WHERE ds BETWEEN {{ start_ds }} and {{ end_ds }}  -- error because ds is a string
```
