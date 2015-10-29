-- schema for local servers to store user info in SQLite

create table account (
   realname varchar(100) not null,
   profession varchar(50) not null,
   username varchar(20) not null,
   organisation varchar(100),
   address varchar(100),
   town varchar (50),
   state varchar (20),
   status char not null, -- A=active, P=provisional, I=inactive
   provider varchar(10),
   encrypted boolean not null default true,
   telephone varchar(20),
   nonce char(10)
   );

create table online (
       username varchar(20) not null,
       logged timestamp not null default now()
       );
      
