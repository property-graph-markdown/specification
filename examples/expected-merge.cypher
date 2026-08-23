MERGE (n0:Person {id:"ada-lovelace"})
SET
    n0.name = "Ada Lovelace",
    n0.born = 1815,
    n0.died = 1852,
    n0.occupation = "Mathematician"
MERGE (n1:Place {id:"london"})
SET
    n1.name = "London",
    n1.country = "United Kingdom",
    n1.category = "City"
MERGE (n2:Person {id:"charles-babbage"})
SET
    n2.name = "Charles Babbage",
    n2.born = 1791,
    n2.died = 1871,
    n2.occupations = ["Mathematician", "Inventor"]
MERGE (n3:Person {id:"augustus-de-morgan"})
SET
    n3.name = "Augustus De Morgan",
    n3.born = 1806,
    n3.died = 1871,
    n3.occupations = ["Mathematician", "Logician"]
MERGE (n4:Design {id:"analytical-engine"})
SET
    n4.name = "Analytical Engine",
    n4.proposed = 1837,
    n4.category = "Computer"
MERGE (n0)-[:born_in {
    year: 1815
}]->(n1)
MERGE (n0)-[:collaborated_with {
    from: 1833
}]->(n2)
MERGE (n0)-[:studied_under {
    from: 1840
}]->(n3)
MERGE (n0)-[:contributed_to {
    role: "notes and algorithm",
    year: 1843
}]->(n4)
MERGE (n2)-[:designed {
    from: 1833
}]->(n4)
