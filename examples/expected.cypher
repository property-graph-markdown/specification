MERGE (n0:PGMConcept {pgm_concept_id:"ada-lovelace"})
SET n0.pgm_resolved = true
SET n0.pgm_type = "Person"
SET n0.pgm_properties_json = "[\"pgm-yaml\",\"v1\",[\"mapping\",[[[\"string\",\"born\"],[\"number\",\"1815\"]],[[\"string\",\"died\"],[\"number\",\"1852\"]],[[\"string\",\"name\"],[\"string\",\"Ada Lovelace\"]],[[\"string\",\"occupation\"],[\"string\",\"Mathematician\"]],[[\"string\",\"type\"],[\"string\",\"Person\"]]]]]"
MERGE (n1:PGMConcept {pgm_concept_id:"analytical-engine"})
SET n1.pgm_resolved = true
SET n1.pgm_type = "Design"
SET n1.pgm_properties_json = "[\"pgm-yaml\",\"v1\",[\"mapping\",[[[\"string\",\"category\"],[\"string\",\"Computer\"]],[[\"string\",\"name\"],[\"string\",\"Analytical Engine\"]],[[\"string\",\"proposed\"],[\"number\",\"1837\"]],[[\"string\",\"type\"],[\"string\",\"Design\"]]]]]"
MERGE (n2:PGMConcept {pgm_concept_id:"augustus-de-morgan"})
SET n2.pgm_resolved = true
SET n2.pgm_type = "Person"
SET n2.pgm_properties_json = "[\"pgm-yaml\",\"v1\",[\"mapping\",[[[\"string\",\"born\"],[\"number\",\"1806\"]],[[\"string\",\"died\"],[\"number\",\"1871\"]],[[\"string\",\"name\"],[\"string\",\"Augustus De Morgan\"]],[[\"string\",\"occupations\"],[\"sequence\",[[\"string\",\"Mathematician\"],[\"string\",\"Logician\"]]]],[[\"string\",\"type\"],[\"string\",\"Person\"]]]]]"
MERGE (n3:PGMConcept {pgm_concept_id:"charles-babbage"})
SET n3.pgm_resolved = true
SET n3.pgm_type = "Person"
SET n3.pgm_properties_json = "[\"pgm-yaml\",\"v1\",[\"mapping\",[[[\"string\",\"born\"],[\"number\",\"1791\"]],[[\"string\",\"died\"],[\"number\",\"1871\"]],[[\"string\",\"name\"],[\"string\",\"Charles Babbage\"]],[[\"string\",\"occupations\"],[\"sequence\",[[\"string\",\"Mathematician\"],[\"string\",\"Inventor\"]]]],[[\"string\",\"type\"],[\"string\",\"Person\"]]]]]"
MERGE (n4:PGMConcept {pgm_concept_id:"london"})
SET n4.pgm_resolved = true
SET n4.pgm_type = "Place"
SET n4.pgm_properties_json = "[\"pgm-yaml\",\"v1\",[\"mapping\",[[[\"string\",\"category\"],[\"string\",\"City\"]],[[\"string\",\"country\"],[\"string\",\"United Kingdom\"]],[[\"string\",\"name\"],[\"string\",\"London\"]],[[\"string\",\"type\"],[\"string\",\"Place\"]]]]]"
CREATE (n0)-[r0:PGM_RELATIONSHIP {pgm_relationship_id:"pgmrel:v1:sha256:5f8b6c640acc4902f029ff8658a404785a4d53e355cdea5cfead39261c4d1db9",pgm_relationship_key:"pgmkey:v1:sha256:423739e4de6eebdb9264aa91ffcac6fdc2691d904342625b0abe74998835b54c",pgm_occurrence:0,pgm_properties_json:"[\"pgm-yaml\",\"v1\",[\"mapping\",[[[\"string\",\"role\"],[\"string\",\"notes and algorithm\"]],[[\"string\",\"type\"],[\"string\",\"contributed_to\"]],[[\"string\",\"year\"],[\"number\",\"1843\"]]]]]",pgm_type:"contributed_to"}]->(n1)
CREATE (n0)-[r1:PGM_RELATIONSHIP {pgm_relationship_id:"pgmrel:v1:sha256:9aac815e680d6cd52bb37548259bd8ebe18c5aed80debd5668097f75a0d37e8c",pgm_relationship_key:"pgmkey:v1:sha256:8eee0d9da8a9548530bf6e73612fcaebbda7a1456382f86a535a68dcd54e7224",pgm_occurrence:0,pgm_properties_json:"[\"pgm-yaml\",\"v1\",[\"mapping\",[[[\"string\",\"from\"],[\"number\",\"1840\"]],[[\"string\",\"type\"],[\"string\",\"studied_under\"]]]]]",pgm_type:"studied_under"}]->(n2)
CREATE (n0)-[r2:PGM_RELATIONSHIP {pgm_relationship_id:"pgmrel:v1:sha256:ab2d76c35991eb796bb1bcd7a08f92e1c670eb09cbbad779fb5938043c29933e",pgm_relationship_key:"pgmkey:v1:sha256:29fdcb4088ed8de80f661c5cac9c224a5108fa3d1660e9cd0068205540c88c2e",pgm_occurrence:0,pgm_properties_json:"[\"pgm-yaml\",\"v1\",[\"mapping\",[[[\"string\",\"from\"],[\"number\",\"1833\"]],[[\"string\",\"type\"],[\"string\",\"collaborated_with\"]]]]]",pgm_type:"collaborated_with"}]->(n3)
CREATE (n0)-[r3:PGM_RELATIONSHIP {pgm_relationship_id:"pgmrel:v1:sha256:aed34a15d136e8e1821ec82f3e93b0440d128f0ae64d98e7fa07835bd61e71d4",pgm_relationship_key:"pgmkey:v1:sha256:62c8ffe79772a2f1b460e107bf79087b83c0a6d1edfcb4b12e75e0c26a88a6ec",pgm_occurrence:0,pgm_properties_json:"[\"pgm-yaml\",\"v1\",[\"mapping\",[[[\"string\",\"type\"],[\"string\",\"born_in\"]],[[\"string\",\"year\"],[\"number\",\"1815\"]]]]]",pgm_type:"born_in"}]->(n4)
CREATE (n3)-[r4:PGM_RELATIONSHIP {pgm_relationship_id:"pgmrel:v1:sha256:4d112866b605f0ab5b7520d737edab3f2040ebe0d941ff7d2aa1ac3f97b29d78",pgm_relationship_key:"pgmkey:v1:sha256:255a9a8253026b73a099f6a191323ef3318afaee1d4d8b8b0dab7100ea9395a8",pgm_occurrence:0,pgm_properties_json:"[\"pgm-yaml\",\"v1\",[\"mapping\",[[[\"string\",\"from\"],[\"number\",\"1833\"]],[[\"string\",\"type\"],[\"string\",\"designed\"]]]]]",pgm_type:"designed"}]->(n1)
