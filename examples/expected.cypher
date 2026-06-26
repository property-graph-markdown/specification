MERGE (n0:Invoice:Document {id:"invoice.md"})
SET
    n0.title = "Invoice 2026-001",
    n0.status = "approved",
    n0.amount = 1532,
    n0.currency = "CHF"
MERGE (n1:Person {id:"peter-meier.md"})
SET
    n1.name = "Peter Meier",
    n1.role = "Finance Manager"
MERGE (n2:Project {id:"project-apollo.md"})
SET
    n2.name = "Project Apollo",
    n2.status = "active"
MERGE (n0)-[:APPROVED_BY {
    date: date("2026-06-26")
}]->(n1)
MERGE (n0)-[:PART_OF]->(n2)
MERGE (n1)-[:MEMBER_OF]->(n2)
