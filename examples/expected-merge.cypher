MERGE (n0:Person:Mathematician {id:"ada-lovelace.md"})
SET
    n0.name = "Ada Lovelace",
    n0.born = 1815,
    n0.died = 1852
MERGE (n1:Place:City {id:"london.md"})
SET
    n1.name = "London",
    n1.country = "United Kingdom"
MERGE (n2:Person:Mathematician:Inventor {id:"charles-babbage.md"})
SET
    n2.name = "Charles Babbage",
    n2.born = 1791,
    n2.died = 1871
MERGE (n3:Person:Mathematician:Logician {id:"augustus-de-morgan.md"})
SET
    n3.name = "Augustus De Morgan",
    n3.born = 1806,
    n3.died = 1871
MERGE (n4:Design:Computer {id:"analytical-engine.md"})
SET
    n4.name = "Analytical Engine",
    n4.proposed = 1837
MERGE (n0)-[:BORN_IN {
    year: 1815
}]->(n1)
MERGE (n0)-[:COLLABORATED_WITH {
    from: 1833
}]->(n2)
MERGE (n0)-[:STUDIED_UNDER {
    from: 1840
}]->(n3)
MERGE (n0)-[:CONTRIBUTED_TO {
    role: "notes and algorithm",
    year: 1843
}]->(n4)
MERGE (n2)-[:DESIGNED {
    from: 1833
}]->(n4)
