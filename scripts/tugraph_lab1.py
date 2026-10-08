# -*- coding: utf-8 -*-
"""
TuGraph 实验1：影人关系图
通过官方 Bolt 协议（兼容 Neo4j 驱动）完成：建模 -> 数据导入 -> 增删改查 -> 聚合查询

依赖：
    pip install neo4j

运行：
    set TUGRAPH_BOLT=101.37.237.115:7687
    set TUGRAPH_PASSWORD=<计算巢实例详情页展示的 admin 密码>
    python tugraph_lab1.py
"""
import json
import os

from neo4j import GraphDatabase

URI = "bolt://" + os.environ.get("TUGRAPH_BOLT", "101.37.237.115:7687")
AUTH = ("admin", os.environ.get("TUGRAPH_PASSWORD", "<实例详情页展示的admin密码>"))
DB = os.environ.get("TUGRAPH_GRAPH", "lab1")

PERSONS = [
    (1001, "James Wan", 1977),
    (1002, "Peter Jackson", 1961),
    (1003, "Christopher Nolan", 1970),
    (1004, "Steven Spielberg", 1946),
]
MOVIES = [
    (2001, "Fast & Furious 7", 2015, 7.1),
    (2002, "The Conjuring", 2013, 7.0),
    (2010, "Aquaman", 2018, 6.9),
    (2003, "The Lord of the Rings: The Return of the King", 2003, 9.0),
    (2004, "The Hobbit: An Unexpected Journey", 2012, 7.8),
    (2005, "Inception", 2010, 9.3),
    (2006, "Interstellar", 2014, 9.4),
    (2011, "Tenet", 2020, 7.3),
    (2007, "Jurassic Park", 1993, 8.2),
]
PRODUCE = [
    (1001, 2001), (1001, 2002), (1001, 2010),
    (1002, 2003), (1002, 2004),
    (1003, 2005), (1003, 2006), (1003, 2011),
    (1004, 2007),
]

PERSON_JSON = json.dumps({
    "label": "person", "primary": "id", "type": "VERTEX",
    "properties": [
        {"name": "id", "type": "INT64"},
        {"name": "name", "type": "STRING"},
        {"name": "born", "type": "INT64", "optional": True},
        {"name": "poster_image", "type": "STRING", "optional": True},
    ],
}, ensure_ascii=False)

MOVIE_JSON = json.dumps({
    "label": "movie", "primary": "id", "type": "VERTEX",
    "properties": [
        {"name": "id", "type": "INT64"},
        {"name": "title", "type": "STRING"},
        {"name": "year", "type": "INT64", "optional": True},
        {"name": "rating", "type": "DOUBLE", "optional": True},
    ],
}, ensure_ascii=False)

PRODUCE_JSON = json.dumps({
    "label": "produce", "type": "EDGE",
    "constraints": [["person", "movie"]],
    "properties": [],
}, ensure_ascii=False)


def run(session, cypher, **kwargs):
    return session.run(cypher, **kwargs).data()


def main():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as s:
            print("=" * 70)
            print("【0】清空图", DB)
            print(run(s, "CALL db.dropDB()"))

            print("=" * 70)
            print("【1】模型建立（点标签 person / movie，边标签 produce）")
            print("createVertexLabelByJson(person) ->",
                  s.run("CALL db.createVertexLabelByJson($j)", j=PERSON_JSON).data())
            print("createVertexLabelByJson(movie)  ->",
                  s.run("CALL db.createVertexLabelByJson($j)", j=MOVIE_JSON).data())
            print("createEdgeLabelByJson(produce)  ->",
                  s.run("CALL db.createEdgeLabelByJson($j)", j=PRODUCE_JSON).data())
            print("当前图模型 schema:")
            print(run(s, "CALL dbms.graph.getGraphSchema()"))

            print("=" * 70)
            print("【2】数据导入")
            for pid, name, born in PERSONS:
                s.run("CREATE (n:person {id:$id, name:$name, born:$born, poster_image:''})",
                      id=pid, name=name, born=born)
            for mid, title, year, rating in MOVIES:
                s.run("CREATE (n:movie {id:$id, title:$title, year:$year, rating:$rating})",
                      id=mid, title=title, year=year, rating=rating)
            for pid, mid in PRODUCE:
                s.run("MATCH (a:person {id:$p}),(b:movie {id:$m}) CREATE (a)-[:produce]->(b)",
                      p=pid, m=mid)
            print("person 数量:", run(s, "MATCH (n:person) RETURN count(n) AS 数量"))
            print("movie  数量:", run(s, "MATCH (n:movie) RETURN count(n) AS 数量"))
            print("produce 数量:", run(s, "MATCH ()-[r:produce]->() RETURN count(r) AS 数量"))

            print("=" * 70)
            print("【3】增删改查")
            print("[查] 前 3 位主创:")
            print(run(s, "MATCH (n:person) RETURN n.id AS id, n.name AS 姓名, n.born AS 出生年 "
                         "ORDER BY n.id LIMIT 3"))
            print("[查] James Wan 制作的电影:")
            print(run(s, "MATCH (p:person {name:'James Wan'})-[:produce]->(m:movie) "
                         "RETURN m.title AS 电影, m.year AS 年份"))
            print("[增] 新增主创 Denis Villeneuve:")
            print(run(s, "CREATE (n:person {id:1005, name:'Denis Villeneuve', born:1967, poster_image:''}) "
                         "RETURN n.id AS id, n.name AS 姓名, n.born AS 出生年"))
            print("[改] 修改出生年 1967 -> 1968，并补充照片:")
            print(run(s, "MATCH (n:person {id:1005}) SET n.born = 1968, n.poster_image = 'dv.jpg' "
                         "RETURN n.id AS id, n.name AS 姓名, n.born AS 出生年, n.poster_image AS 照片"))
            print("[删] 删除 Denis Villeneuve:")
            print(run(s, "MATCH (n:person {id:1005}) DELETE n"))
            print("删除后 person 总数:", run(s, "MATCH (n:person) RETURN count(n) AS 数量"))

            print("=" * 70)
            print("【4】聚合查询（自设计）")
            print("例1：统计每位制片人制作的电影数量与平均评分，按电影数降序:")
            print(run(s,
                      "MATCH (p:person)-[:produce]->(m:movie) "
                      "RETURN p.name AS 制片人, count(m) AS 电影数, avg(m.rating) AS 平均评分 "
                      "ORDER BY 电影数 DESC, 平均评分 DESC"))
            print("例2：WITH 多段聚合，找出制作电影数>=2 且平均评分>8 的制片人:")
            print(run(s,
                      "MATCH (p:person)-[:produce]->(m:movie) "
                      "WITH p, count(m) AS 电影数, avg(m.rating) AS 平均评分 "
                      "WHERE 电影数 >= 2 AND 平均评分 > 8 "
                      "RETURN p.name AS 制片人, 电影数, 平均评分 ORDER BY 平均评分 DESC"))
            print("例3：各年份电影数量分布:")
            print(run(s, "MATCH (m:movie) RETURN m.year AS 年份, count(m) AS 数量 ORDER BY 年份"))
    finally:
        driver.close()


if __name__ == "__main__":
    main()
