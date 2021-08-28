drop table link_endpoints; 
drop table endpoints;
drop table practitioner_role; 
drop table practitioners; 
drop table organisations;
drop table audit;
drop table certificates;
create table certificates (
       fingerprint text not null primary key,
       expiry timestamp with time zone not null,
       revoked boolean not null default false,
       content text not null,
       verified boolean not null default false,
       verification_code text
 );


create table audit (
       id_audit serial primary key,
       fk_created integer references audit (id_audit),
       time_updated timestamp with time zone not null default now(),
       origin inet not null,
       fk_cert text not null references certificates (fingerprint)
 );


create table organisations (
       fk_audit integer not null unique references audit (id_audit),
       "name" text,
       active boolean not null default true,
       jdoc jsonb not null
 );


create table practitioners (
       fk_audit integer not null unique references audit (id_audit),
       surname text,
       firstname text not null,
       active boolean not null default true,
       jdoc jsonb not null
);


create table practitioner_role (
       fk_audit integer not null references audit (id_audit),
       fk_prac integer not null references practitioners (fk_audit),
       fk_org integer references organisations (fk_audit),
       active boolean not null default true,
       jdoc jsonb not null
 );


create table endpoints (
       fk_audit integer not null unique references audit (id_audit),
       status text not null,
       url text not null,
       jdoc jsonb not null
);

create table link_endpoints (
       fk_endpoint integer not null references endpoints (fk_audit),
       fk_prac_org integer not null references audit (id_audit)
);

create or replace view vworganisations as
       with orgs1 as (select
       	    coalesce(fk_created, id_audit) as id_created,
	    time_updated,
	    id_audit,
	    "name",
	    active,
	    jdoc
	 from organisations, audit where
	 id_audit = fk_audit),
	 orgs2 as (select distinct on (id_created) * from orgs1 order by id_created ,time_updated)
	 select * from orgs2 where active; 


create table endpoints (
       fk_audit integer not null references audit (id_audit),
       status text not null,
       url text not null,
       jdoc jsonb not null
);
