CREATE USER testdata IDENTIFIED BY testdata;
GRANT connect, resource TO testdata;
CONNECT testdata/testdata@orcl
DROP TABLE species;
CREATE TABLE species (
    id   NUMBER(6,0)  CONSTRAINT xpk_species PRIMARY KEY
                      CONSTRAINT xnn1_species NOT NULL,
    name VARCHAR2(40) CONSTRAINT xnn2_species NOT NULL );

INSERT INTO species VALUES (0, 'turtle');
INSERT INTO species VALUES (1, 'python');
INSERT INTO species VALUES (2, 'parrot');


