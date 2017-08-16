-- demo:demo
INSERT INTO twitter_user (id, username, password, birth_date) VALUES (1, 'demo', 'fe01ce2a7fbac8fafaed7c982a04e229', '2016-01-26');
-- admin:admin
INSERT INTO twitter_user (id, username, password, birth_date) VALUES (2, 'admin', '21232f297a57a5a743894a0e4a801fc3', '2016-07-06');

INSERT INTO tweet (user_id, content) VALUES (1, 'Hello World!');
INSERT INTO tweet (user_id, content) VALUES (1, 'This is so awesome');
INSERT INTO tweet (user_id, content) VALUES (2, 'Testing twitter clone');
