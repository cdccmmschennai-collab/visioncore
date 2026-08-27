--
-- PostgreSQL database dump
--

\restrict NuHgvs0W3HtROjZJRQPaqe4NILjydIo3sBu5yzetfCZVjhvyqA8QaLaqLAp3iU8

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: activity_action; Type: TYPE; Schema: public; Owner: visioncore
--

CREATE TYPE public.activity_action AS ENUM (
    'login',
    'upload',
    'extract',
    'edit',
    'download',
    'duplicate_blocked',
    'user_created',
    'user_updated',
    'password_reset'
);


ALTER TYPE public.activity_action OWNER TO visioncore;

--
-- Name: batch_status; Type: TYPE; Schema: public; Owner: visioncore
--

CREATE TYPE public.batch_status AS ENUM (
    'uploaded',
    'processing',
    'completed',
    'failed',
    'partial'
);


ALTER TYPE public.batch_status OWNER TO visioncore;

--
-- Name: item_status; Type: TYPE; Schema: public; Owner: visioncore
--

CREATE TYPE public.item_status AS ENUM (
    'uploaded',
    'extracting',
    'processing',
    'completed',
    'failed',
    'duplicate'
);


ALTER TYPE public.item_status OWNER TO visioncore;

--
-- Name: user_role; Type: TYPE; Schema: public; Owner: visioncore
--

CREATE TYPE public.user_role AS ENUM (
    'admin',
    'user'
);


ALTER TYPE public.user_role OWNER TO visioncore;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activities; Type: TABLE; Schema: public; Owner: visioncore
--

CREATE TABLE public.activities (
    id integer NOT NULL,
    user_id integer,
    action public.activity_action NOT NULL,
    tag_number character varying(128),
    description character varying(255),
    detail character varying(512),
    meta jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.activities OWNER TO visioncore;

--
-- Name: activities_id_seq; Type: SEQUENCE; Schema: public; Owner: visioncore
--

CREATE SEQUENCE public.activities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.activities_id_seq OWNER TO visioncore;

--
-- Name: activities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: visioncore
--

ALTER SEQUENCE public.activities_id_seq OWNED BY public.activities.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: visioncore
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO visioncore;

--
-- Name: api_usage; Type: TABLE; Schema: public; Owner: visioncore
--

CREATE TABLE public.api_usage (
    id integer NOT NULL,
    user_id integer,
    tag_number character varying(128),
    model character varying(64) NOT NULL,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    cost_usd double precision DEFAULT '0'::double precision NOT NULL,
    latency_ms integer DEFAULT 0 NOT NULL,
    success boolean DEFAULT true NOT NULL,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.api_usage OWNER TO visioncore;

--
-- Name: api_usage_id_seq; Type: SEQUENCE; Schema: public; Owner: visioncore
--

CREATE SEQUENCE public.api_usage_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.api_usage_id_seq OWNER TO visioncore;

--
-- Name: api_usage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: visioncore
--

ALTER SEQUENCE public.api_usage_id_seq OWNED BY public.api_usage.id;


--
-- Name: asset_tags; Type: TABLE; Schema: public; Owner: visioncore
--

CREATE TABLE public.asset_tags (
    id integer NOT NULL,
    tag_number character varying(128) NOT NULL,
    description character varying(255) NOT NULL,
    ai_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    final_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    ai_excel_path character varying(512),
    template_excel_path character varying(512),
    edited_by_id integer,
    created_by_id integer,
    revision integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.asset_tags OWNER TO visioncore;

--
-- Name: asset_tags_id_seq; Type: SEQUENCE; Schema: public; Owner: visioncore
--

CREATE SEQUENCE public.asset_tags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.asset_tags_id_seq OWNER TO visioncore;

--
-- Name: asset_tags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: visioncore
--

ALTER SEQUENCE public.asset_tags_id_seq OWNED BY public.asset_tags.id;


--
-- Name: batch_items; Type: TABLE; Schema: public; Owner: visioncore
--

CREATE TABLE public.batch_items (
    id integer NOT NULL,
    batch_id integer NOT NULL,
    asset_tag_id integer,
    tag_number character varying(128) NOT NULL,
    description character varying(255) NOT NULL,
    status public.item_status DEFAULT 'uploaded'::public.item_status NOT NULL,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.batch_items OWNER TO visioncore;

--
-- Name: batch_items_id_seq; Type: SEQUENCE; Schema: public; Owner: visioncore
--

CREATE SEQUENCE public.batch_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.batch_items_id_seq OWNER TO visioncore;

--
-- Name: batch_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: visioncore
--

ALTER SEQUENCE public.batch_items_id_seq OWNED BY public.batch_items.id;


--
-- Name: batches; Type: TABLE; Schema: public; Owner: visioncore
--

CREATE TABLE public.batches (
    id integer NOT NULL,
    reference character varying(32) NOT NULL,
    user_id integer NOT NULL,
    status public.batch_status DEFAULT 'uploaded'::public.batch_status NOT NULL,
    total_images integer DEFAULT 0 NOT NULL,
    total_tags integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.batches OWNER TO visioncore;

--
-- Name: batches_id_seq; Type: SEQUENCE; Schema: public; Owner: visioncore
--

CREATE SEQUENCE public.batches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.batches_id_seq OWNER TO visioncore;

--
-- Name: batches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: visioncore
--

ALTER SEQUENCE public.batches_id_seq OWNED BY public.batches.id;


--
-- Name: org_credits; Type: TABLE; Schema: public; Owner: visioncore
--

CREATE TABLE public.org_credits (
    id integer NOT NULL,
    total_purchased_usd double precision NOT NULL,
    updated_by_user_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    ledger_usage_usd double precision NOT NULL,
    ledger_through_date date
);


ALTER TABLE public.org_credits OWNER TO visioncore;

--
-- Name: org_credits_id_seq; Type: SEQUENCE; Schema: public; Owner: visioncore
--

CREATE SEQUENCE public.org_credits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.org_credits_id_seq OWNER TO visioncore;

--
-- Name: org_credits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: visioncore
--

ALTER SEQUENCE public.org_credits_id_seq OWNED BY public.org_credits.id;


--
-- Name: tag_images; Type: TABLE; Schema: public; Owner: visioncore
--

CREATE TABLE public.tag_images (
    id integer NOT NULL,
    item_id integer NOT NULL,
    original_filename character varying(512) NOT NULL,
    stored_path character varying(512) NOT NULL,
    media_type character varying(64) NOT NULL,
    size_bytes integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    content_hash character varying(64)
);


ALTER TABLE public.tag_images OWNER TO visioncore;

--
-- Name: tag_images_id_seq; Type: SEQUENCE; Schema: public; Owner: visioncore
--

CREATE SEQUENCE public.tag_images_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tag_images_id_seq OWNER TO visioncore;

--
-- Name: tag_images_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: visioncore
--

ALTER SEQUENCE public.tag_images_id_seq OWNED BY public.tag_images.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: visioncore
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(64) NOT NULL,
    email character varying(255),
    full_name character varying(128),
    hashed_password character varying(255) NOT NULL,
    role public.user_role DEFAULT 'user'::public.user_role NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    last_login_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO visioncore;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: visioncore
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO visioncore;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: visioncore
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: activities id; Type: DEFAULT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.activities ALTER COLUMN id SET DEFAULT nextval('public.activities_id_seq'::regclass);


--
-- Name: api_usage id; Type: DEFAULT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.api_usage ALTER COLUMN id SET DEFAULT nextval('public.api_usage_id_seq'::regclass);


--
-- Name: asset_tags id; Type: DEFAULT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.asset_tags ALTER COLUMN id SET DEFAULT nextval('public.asset_tags_id_seq'::regclass);


--
-- Name: batch_items id; Type: DEFAULT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.batch_items ALTER COLUMN id SET DEFAULT nextval('public.batch_items_id_seq'::regclass);


--
-- Name: batches id; Type: DEFAULT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.batches ALTER COLUMN id SET DEFAULT nextval('public.batches_id_seq'::regclass);


--
-- Name: org_credits id; Type: DEFAULT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.org_credits ALTER COLUMN id SET DEFAULT nextval('public.org_credits_id_seq'::regclass);


--
-- Name: tag_images id; Type: DEFAULT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.tag_images ALTER COLUMN id SET DEFAULT nextval('public.tag_images_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: activities; Type: TABLE DATA; Schema: public; Owner: visioncore
--

COPY public.activities (id, user_id, action, tag_number, description, detail, meta, created_at, updated_at) FROM stdin;
1	1	login	\N	\N	Signed in	{}	2026-08-07 11:01:56.336971+00	2026-08-07 11:01:56.336971+00
2	1	login	\N	\N	Signed in	{}	2026-08-07 11:09:01.310371+00	2026-08-07 11:09:01.310371+00
3	1	upload	\N	\N	Uploaded 5 image(s) across 5 tag(s)	{"batch_reference": "B-20260807-E8046D"}	2026-08-07 11:15:09.338916+00	2026-08-07 11:15:09.338916+00
4	2	login	\N	\N	Signed in	{}	2026-08-07 11:46:58.556523+00	2026-08-07 11:46:58.556523+00
5	1	login	\N	\N	Signed in	{}	2026-08-11 04:41:44.655775+00	2026-08-11 04:41:44.655775+00
6	2	login	\N	\N	Signed in	{}	2026-08-11 04:49:17.33297+00	2026-08-11 04:49:17.33297+00
7	1	login	\N	\N	Signed in	{}	2026-08-11 04:50:14.103336+00	2026-08-11 04:50:14.103336+00
8	1	upload	\N	\N	Uploaded 5 image(s) across 5 tag(s)	{"batch_reference": "B-20260811-0AD3FE"}	2026-08-11 06:54:41.59601+00	2026-08-11 06:54:41.59601+00
9	2	login	\N	\N	Signed in	{}	2026-08-11 08:21:56.954199+00	2026-08-11 08:21:56.954199+00
10	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260811-DBD8C2"}	2026-08-11 08:22:29.827096+00	2026-08-11 08:22:29.827096+00
11	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260811-8DEDE7"}	2026-08-11 08:27:08.914029+00	2026-08-11 08:27:08.914029+00
12	2	login	\N	\N	Signed in	{}	2026-08-11 08:41:57.463156+00	2026-08-11 08:41:57.463156+00
13	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260811-56BFFA"}	2026-08-11 08:43:04.665919+00	2026-08-11 08:43:04.665919+00
14	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260811-63EE81"}	2026-08-11 09:15:16.713778+00	2026-08-11 09:15:16.713778+00
15	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260811-D35509"}	2026-08-11 09:20:10.199839+00	2026-08-11 09:20:10.199839+00
16	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260811-567ACE"}	2026-08-11 09:38:18.371976+00	2026-08-11 09:38:18.371976+00
218	2	login	\N	\N	Signed in	{}	2026-08-17 09:59:01.234884+00	2026-08-17 09:59:01.234884+00
224	2	download	12-4020-BV-0074	BALL VALVE	Downloaded AI Output workbook	{}	2026-08-17 10:02:31.518085+00	2026-08-17 10:02:31.518085+00
227	2	download	12-4020-BV-0074	BALL VALVE	Downloaded AI Output workbook	{}	2026-08-17 10:04:25.188517+00	2026-08-17 10:04:25.188517+00
229	2	extract	12-4020-CC-0032	CORROSION COUPON	Extracted from 1 photo(s)	{"cost_usd": 0.0, "input_tokens": 1833, "output_tokens": 470}	2026-08-17 10:05:50.505095+00	2026-08-17 10:05:50.505095+00
21	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260811-C7921A"}	2026-08-11 09:43:16.908469+00	2026-08-11 09:43:16.908469+00
22	2	upload	\N	\N	Uploaded 5 image(s) across 5 tag(s)	{"batch_reference": "B-20260811-4357CA"}	2026-08-11 09:43:57.316407+00	2026-08-11 09:43:57.316407+00
230	2	login	\N	\N	Signed in	{}	2026-08-17 10:15:31.567074+00	2026-08-17 10:15:31.567074+00
231	2	login	\N	\N	Signed in	{}	2026-08-17 10:19:42.077434+00	2026-08-17 10:19:42.077434+00
232	2	login	\N	\N	Signed in	{}	2026-08-17 10:31:56.332399+00	2026-08-17 10:31:56.332399+00
244	2	download	74-FG-024	GAUGE,SIGHT GLASS	Downloaded Template workbook	{}	2026-08-17 10:46:25.657337+00	2026-08-17 10:46:25.657337+00
245	2	upload	12	IJBF-1067-FIRE AND GAS JUNCTION BOX	Uploaded 1 image(s)	{"item_id": 99, "batch_id": 57, "batch_reference": "B-20260817-F4239C"}	2026-08-17 10:57:38.274319+00	2026-08-17 10:57:38.274319+00
246	2	extract	12	IJBF-1067-FIRE AND GAS JUNCTION BOX	Extracted from 1 photo(s)	{"cost_usd": 0.0, "input_tokens": 1830, "output_tokens": 385}	2026-08-17 10:59:02.35202+00	2026-08-17 10:59:02.35202+00
252	2	upload	12-4020-DBV-0004	DOUBLE BLOCK AND BLEED VALVE	Uploaded 1 image(s)	{"item_id": 100, "batch_id": 58, "batch_reference": "B-20260818-F3DBC6"}	2026-08-18 04:56:30.807109+00	2026-08-18 04:56:30.807109+00
30	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260811-5A0007"}	2026-08-11 09:50:17.789653+00	2026-08-11 09:50:17.789653+00
259	2	download	12	IJBF-1067-FIRE AND GAS JUNCTION BOX	Downloaded AI Output workbook	{}	2026-08-18 05:07:01.136451+00	2026-08-18 05:07:01.136451+00
264	1	user_updated	\N	\N	Updated user User1	{}	2026-08-18 05:55:24.881742+00	2026-08-18 05:55:24.881742+00
268	1	user_updated	\N	\N	Updated user user1	{}	2026-08-18 06:00:25.345989+00	2026-08-18 06:00:25.345989+00
270	2	upload	12-4020-FE-0031	FLOW ELEMENT	Uploaded 1 image(s)	{"item_id": 104, "batch_id": 62, "batch_reference": "B-20260818-B86933"}	2026-08-18 06:08:25.333487+00	2026-08-18 06:08:25.333487+00
271	2	extract	12-4020-FE-0031	FLOW ELEMENT	Extracted from 1 photo(s)	{"cost_usd": 0.029304, "input_tokens": 5858, "output_tokens": 782}	2026-08-18 06:08:35.264838+00	2026-08-18 06:08:35.264838+00
36	2	upload	\N	\N	Uploaded 5 image(s) across 5 tag(s)	{"batch_reference": "B-20260811-4E418B"}	2026-08-11 09:50:34.685989+00	2026-08-11 09:50:34.685989+00
274	2	extract	21-JDD-01	JUNCTION BOX,INSTRUMENT	Extracted from 1 photo(s)	{"cost_usd": 0.028584, "input_tokens": 5863, "output_tokens": 733}	2026-08-18 06:26:23.586777+00	2026-08-18 06:26:23.586777+00
38	2	upload	\N	\N	Uploaded 5 image(s) across 5 tag(s)	{"batch_reference": "B-20260811-F44528"}	2026-08-11 09:52:15.294466+00	2026-08-11 09:52:15.294466+00
275	1	login	\N	\N	Signed in	{}	2026-08-18 06:34:49.100532+00	2026-08-18 06:34:49.100532+00
278	2	edit	12-4021-TE-1001	TEMPERATURE ELEMENT	Saved revision 2	{}	2026-08-18 08:31:00.276281+00	2026-08-18 08:31:00.276281+00
281	2	login	\N	\N	Signed in	{}	2026-08-18 08:56:06.019845+00	2026-08-18 08:56:06.019845+00
287	2	login	\N	\N	Signed in	{}	2026-08-18 09:24:06.583644+00	2026-08-18 09:24:06.583644+00
293	2	login	\N	\N	Signed in	{}	2026-08-18 10:29:33.068406+00	2026-08-18 10:29:33.068406+00
295	1	password_reset	\N	\N	Reset password for User1	{}	2026-08-18 10:36:39.840817+00	2026-08-18 10:36:39.840817+00
45	1	login	\N	\N	Signed in	{}	2026-08-11 11:22:27.898397+00	2026-08-11 11:22:27.898397+00
46	2	login	\N	\N	Signed in	{}	2026-08-11 11:22:57.646415+00	2026-08-11 11:22:57.646415+00
47	2	login	\N	\N	Signed in	{}	2026-08-11 11:28:46.187538+00	2026-08-11 11:28:46.187538+00
48	2	login	\N	\N	Signed in	{}	2026-08-11 11:29:00.238359+00	2026-08-11 11:29:00.238359+00
49	1	login	\N	\N	Signed in	{}	2026-08-11 11:32:25.146166+00	2026-08-11 11:32:25.146166+00
50	1	login	\N	\N	Signed in	{}	2026-08-11 11:33:35.484775+00	2026-08-11 11:33:35.484775+00
51	2	login	\N	\N	Signed in	{}	2026-08-11 11:52:31.301539+00	2026-08-11 11:52:31.301539+00
52	2	login	\N	\N	Signed in	{}	2026-08-11 11:52:54.837667+00	2026-08-11 11:52:54.837667+00
53	2	login	\N	\N	Signed in	{}	2026-08-11 11:53:25.849034+00	2026-08-11 11:53:25.849034+00
54	2	login	\N	\N	Signed in	{}	2026-08-11 12:07:05.166577+00	2026-08-11 12:07:05.166577+00
55	2	login	\N	\N	Signed in	{}	2026-08-11 12:07:45.847815+00	2026-08-11 12:07:45.847815+00
56	2	login	\N	\N	Signed in	{}	2026-08-12 03:58:59.528347+00	2026-08-12 03:58:59.528347+00
57	1	login	\N	\N	Signed in	{}	2026-08-12 04:04:28.093724+00	2026-08-12 04:04:28.093724+00
58	1	login	\N	\N	Signed in	{}	2026-08-12 04:21:30.017391+00	2026-08-12 04:21:30.017391+00
59	2	login	\N	\N	Signed in	{}	2026-08-12 04:23:40.618417+00	2026-08-12 04:23:40.618417+00
60	2	download	\N	\N	Downloaded consolidated Template workbook (10 tag(s))	{}	2026-08-12 04:39:26.783307+00	2026-08-12 04:39:26.783307+00
304	1	password_reset	\N	\N	Reset password for user1	{}	2026-08-18 11:07:45.908089+00	2026-08-18 11:07:45.908089+00
312	1	login	\N	\N	Signed in	{}	2026-08-19 05:05:51.013563+00	2026-08-19 05:05:51.013563+00
313	1	login	\N	\N	Signed in	{}	2026-08-19 05:41:38.981983+00	2026-08-19 05:41:38.981983+00
317	2	login	\N	\N	Signed in	{}	2026-08-19 07:02:23.601719+00	2026-08-19 07:02:23.601719+00
318	2	duplicate_blocked	21-JDD-01	JUNCTION BOX,INSTRUMENT	Tag already extracted — existing record shown	{}	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:41.831303+00
319	2	duplicate_blocked	22-GV-0550	VALVE,GATE	Tag already extracted — existing record shown	{}	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:41.831303+00
320	2	upload	22-GV-0553	VALVE,GATE	Uploaded 1 image(s)	{"item_id": 113, "batch_id": 69, "batch_reference": "B-20260819-10430B"}	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:41.831303+00
321	2	upload	22-LT-702	TRANSMITTER,LEVEL	Uploaded 1 image(s)	{"item_id": 114, "batch_id": 69, "batch_reference": "B-20260819-10430B"}	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:41.831303+00
334	1	login	\N	\N	Signed in	{}	2026-08-19 08:17:02.074415+00	2026-08-19 08:17:02.074415+00
62	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260812-2E7DC6"}	2026-08-12 04:52:55.775175+00	2026-08-12 04:52:55.775175+00
219	1	login	\N	\N	Signed in	{}	2026-08-17 09:59:23.971756+00	2026-08-17 09:59:23.971756+00
226	2	download	12-4020-BV-0074	BALL VALVE	Downloaded Template workbook	{}	2026-08-17 10:04:11.873268+00	2026-08-17 10:04:11.873268+00
239	2	extract	54-038-P12	EXTINGUISHER,DRY POWDER	Extracted from 1 photo(s)	{"cost_usd": 0.0, "input_tokens": 1858, "output_tokens": 393}	2026-08-17 10:41:51.6822+00	2026-08-17 10:41:51.6822+00
243	2	edit	74-FG-024	GAUGE,SIGHT GLASS	Saved revision 2	{}	2026-08-17 10:46:03.723937+00	2026-08-17 10:46:03.723937+00
249	2	download	73-BV-0023	VALVE,BALL	Downloaded Template workbook	{}	2026-08-17 11:07:24.09548+00	2026-08-17 11:07:24.09548+00
253	2	extract	12-4020-DBV-0004	DOUBLE BLOCK AND BLEED VALVE	Extracted from 1 photo(s)	{"cost_usd": 0.028383, "input_tokens": 3821, "output_tokens": 1128}	2026-08-18 04:56:44.374848+00	2026-08-18 04:56:44.374848+00
69	2	upload	\N	\N	Uploaded 10 image(s) across 10 tag(s)	{"batch_reference": "B-20260812-C5512C"}	2026-08-12 04:54:12.220674+00	2026-08-12 04:54:12.220674+00
254	2	download	12-4020-DBV-0004	DOUBLE BLOCK AND BLEED VALVE	Downloaded AI Output workbook	{}	2026-08-18 04:57:01.749781+00	2026-08-18 04:57:01.749781+00
260	2	duplicate_blocked	12	LJBF-1067-FIRE AND GAS JUNCTION BOX	Tag already extracted — existing record shown	{}	2026-08-18 05:18:45.395007+00	2026-08-18 05:18:45.395007+00
265	1	user_updated	\N	\N	Updated user user1	{}	2026-08-18 05:55:57.432835+00	2026-08-18 05:55:57.432835+00
269	2	login	\N	\N	Signed in	{}	2026-08-18 06:06:33.340139+00	2026-08-18 06:06:33.340139+00
74	2	download	\N	\N	Downloaded consolidated Template workbook (14 tag(s))	{}	2026-08-12 05:06:06.293302+00	2026-08-12 05:06:06.293302+00
75	2	upload	\N	\N	Uploaded 3 image(s) across 3 tag(s)	{"batch_reference": "B-20260812-29E870"}	2026-08-12 05:17:11.655423+00	2026-08-12 05:17:11.655423+00
282	2	login	\N	\N	Signed in	{}	2026-08-18 09:00:39.523217+00	2026-08-18 09:00:39.523217+00
77	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260812-8E4FC3"}	2026-08-12 05:31:02.577126+00	2026-08-12 05:31:02.577126+00
78	1	login	\N	\N	Signed in	{}	2026-08-12 05:39:26.17975+00	2026-08-12 05:39:26.17975+00
79	1	login	\N	\N	Signed in	{}	2026-08-12 05:39:36.024818+00	2026-08-12 05:39:36.024818+00
80	1	login	\N	\N	Signed in	{}	2026-08-12 05:42:58.663014+00	2026-08-12 05:42:58.663014+00
81	2	login	\N	\N	Signed in	{}	2026-08-12 05:45:30.029125+00	2026-08-12 05:45:30.029125+00
288	2	login	\N	\N	Signed in	{}	2026-08-18 09:24:33.488398+00	2026-08-18 09:24:33.488398+00
83	1	upload	\N	\N	Uploaded 5 image(s) across 3 tag(s)	{"batch_reference": "B-20260812-322B0E"}	2026-08-12 05:48:09.320268+00	2026-08-12 05:48:09.320268+00
84	1	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260812-DCEAF0"}	2026-08-12 05:52:46.660024+00	2026-08-12 05:52:46.660024+00
289	2	login	\N	\N	Signed in	{}	2026-08-18 09:30:42.876928+00	2026-08-18 09:30:42.876928+00
294	1	login	\N	\N	Signed in	{}	2026-08-18 10:36:12.308445+00	2026-08-18 10:36:12.308445+00
296	4	login	\N	\N	Signed in	{}	2026-08-18 10:37:06.355452+00	2026-08-18 10:37:06.355452+00
88	2	upload	\N	\N	Uploaded 4 image(s) across 4 tag(s)	{"batch_reference": "B-20260812-DD2FCA"}	2026-08-12 06:33:40.562901+00	2026-08-12 06:33:40.562901+00
89	2	download	\N	\N	Downloaded consolidated Template workbook (15 tag(s))	{}	2026-08-12 06:57:56.986941+00	2026-08-12 06:57:56.986941+00
307	2	login	\N	\N	Signed in	{}	2026-08-18 11:11:18.994452+00	2026-08-18 11:11:18.994452+00
314	1	upload	12-ECP-0002	ELECTRIC CONTROL PANEL	Uploaded 1 image(s)	{"item_id": 109, "batch_id": 67, "batch_reference": "B-20260819-59EEA7"}	2026-08-19 05:42:46.21322+00	2026-08-19 05:42:46.21322+00
92	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260812-30CFB7"}	2026-08-12 07:13:41.916385+00	2026-08-12 07:13:41.916385+00
93	1	login	\N	\N	Signed in	{}	2026-08-12 07:22:14.615598+00	2026-08-12 07:22:14.615598+00
94	1	login	\N	\N	Signed in	{}	2026-08-12 08:13:19.368685+00	2026-08-12 08:13:19.368685+00
95	2	login	\N	\N	Signed in	{}	2026-08-12 09:10:49.366409+00	2026-08-12 09:10:49.366409+00
315	1	extract	12-ECP-0002	ELECTRIC CONTROL PANEL	Extracted from 1 photo(s)	{"cost_usd": 0.037251, "input_tokens": 5862, "output_tokens": 1311}	2026-08-19 05:43:01.841406+00	2026-08-19 05:43:01.841406+00
97	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_reference": "B-20260812-8A1891"}	2026-08-12 09:11:24.366876+00	2026-08-12 09:11:24.366876+00
98	2	download	\N	\N	Downloaded consolidated Template workbook (15 tag(s))	{}	2026-08-12 09:16:38.080238+00	2026-08-12 09:16:38.080238+00
99	2	download	\N	\N	Downloaded consolidated Template workbook (15 tag(s))	{}	2026-08-12 09:17:20.403912+00	2026-08-12 09:17:20.403912+00
100	1	login	\N	\N	Signed in	{}	2026-08-12 09:35:33.014926+00	2026-08-12 09:35:33.014926+00
101	1	upload	\N	\N	Uploaded 2 image(s) across 2 tag(s)	{"batch_id": 23, "batch_reference": "B-20260812-2620CD"}	2026-08-12 09:35:58.112443+00	2026-08-12 09:35:58.112443+00
316	1	duplicate_blocked	12-4020-BV-0074	BALL VALVE	Tag already extracted — existing record shown	{}	2026-08-19 05:46:05.656309+00	2026-08-19 05:46:05.656309+00
325	2	upload	51-PT-701	TRANSMITTER,PRESSURE	Uploaded 1 image(s)	{"item_id": 116, "batch_id": 70, "batch_reference": "B-20260819-06E6C0"}	2026-08-19 07:08:30.747465+00	2026-08-19 07:08:30.747465+00
331	2	download	\N	\N	Downloaded consolidated Template workbook (18 tag(s))	{}	2026-08-19 08:11:10.375203+00	2026-08-19 08:11:10.375203+00
336	1	login	\N	\N	Signed in	{}	2026-08-19 08:18:17.471889+00	2026-08-19 08:18:17.471889+00
106	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_id": 24, "batch_reference": "B-20260812-A295FF"}	2026-08-12 10:30:13.575849+00	2026-08-12 10:30:13.575849+00
340	3	login	\N	\N	Signed in	{}	2026-08-19 08:19:08.824757+00	2026-08-19 08:19:08.824757+00
108	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_id": 25, "batch_reference": "B-20260812-1D5A6D"}	2026-08-12 10:30:53.517806+00	2026-08-12 10:30:53.517806+00
342	3	login	\N	\N	Signed in	{}	2026-08-19 08:22:30.459954+00	2026-08-19 08:22:30.459954+00
343	3	duplicate_blocked	21-JDD-01	JUNCTION BOX,INSTRUMENT	Tag already extracted — existing record shown	{}	2026-08-19 08:24:31.575019+00	2026-08-19 08:24:31.575019+00
111	2	download	\N	\N	Downloaded consolidated Template workbook (17 tag(s))	{}	2026-08-12 10:31:22.122322+00	2026-08-12 10:31:22.122322+00
346	3	download	21-JDD-01	JUNCTION BOX,INSTRUMENT	Downloaded Template workbook	{}	2026-08-19 08:26:02.196693+00	2026-08-19 08:26:02.196693+00
348	3	login	\N	\N	Signed in	{}	2026-08-19 09:04:23.636392+00	2026-08-19 09:04:23.636392+00
352	3	upload	12-4020-FDI-21-0003	INFRARED FLAME DETECTOR	Uploaded 1 image(s)	{"item_id": 121, "batch_id": 75, "batch_reference": "B-20260819-8DD594"}	2026-08-19 09:35:42.715478+00	2026-08-19 09:35:42.715478+00
115	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_id": 26, "batch_reference": "B-20260812-47C8D8"}	2026-08-12 10:37:48.754832+00	2026-08-12 10:37:48.754832+00
353	3	upload	12-4020-NLV-0007	NEEDLE VALVE	Uploaded 2 image(s)	{"item_id": 122, "batch_id": 75, "batch_reference": "B-20260819-8DD594"}	2026-08-19 09:35:42.715478+00	2026-08-19 09:35:42.715478+00
117	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_id": 27, "batch_reference": "B-20260812-C828F3"}	2026-08-12 10:39:10.245324+00	2026-08-12 10:39:10.245324+00
362	3	login	\N	\N	Signed in	{}	2026-08-19 10:13:14.973321+00	2026-08-19 10:13:14.973321+00
363	2	login	\N	\N	Signed in	{}	2026-08-19 10:15:33.486703+00	2026-08-19 10:15:33.486703+00
368	3	duplicate_blocked	12-4020-NLV-0007	NEEDLE VALVE	Tag already extracted — existing record shown	{}	2026-08-19 11:08:06.802404+00	2026-08-19 11:08:06.802404+00
370	3	extract	12-GDF-03-0103	FLAMMABLE GAS DETECTOR	Extracted from 2 photo(s)	{"cost_usd": 0.063147, "input_tokens": 10619, "output_tokens": 2086}	2026-08-19 11:10:20.185873+00	2026-08-19 11:10:20.185873+00
372	3	upload	12-M2-DBV-0002	DOUBLE BLOCK AND BLEED VALVE	Uploaded 2 image(s)	{"item_id": 129, "batch_id": 81, "batch_reference": "B-20260819-5F5B24"}	2026-08-19 11:15:23.201615+00	2026-08-19 11:15:23.201615+00
376	3	download	12-M2-DBV-0002	DOUBLE BLOCK AND BLEED VALVE	Downloaded Template workbook	{}	2026-08-19 11:17:38.849558+00	2026-08-19 11:17:38.849558+00
220	2	login	\N	\N	Signed in	{}	2026-08-17 10:01:03.94235+00	2026-08-17 10:01:03.94235+00
225	2	download	12-4020-BV-0074	BALL VALVE	Downloaded AI Output workbook	{}	2026-08-17 10:04:10.839853+00	2026-08-17 10:04:10.839853+00
233	2	upload	74-FG-024	GAUGE,SIGHT GLASS	Uploaded 1 image(s)	{"item_id": 94, "batch_id": 56, "batch_reference": "B-20260817-8DFACD"}	2026-08-17 10:38:15.386386+00	2026-08-17 10:38:15.386386+00
121	2	upload	\N	\N	Uploaded 1 image(s) across 1 tag(s)	{"batch_id": 28, "batch_reference": "B-20260812-D4505A"}	2026-08-12 10:58:04.647335+00	2026-08-12 10:58:04.647335+00
122	1	login	\N	\N	Signed in	{}	2026-08-12 11:10:25.23296+00	2026-08-12 11:10:25.23296+00
234	2	upload	54-038-P12	EXTINGUISHER,DRY POWDER	Uploaded 1 image(s)	{"item_id": 95, "batch_id": 56, "batch_reference": "B-20260817-8DFACD"}	2026-08-17 10:38:15.386386+00	2026-08-17 10:38:15.386386+00
235	2	upload	71-FV-003	VALVE,CONTROL,FLOW	Uploaded 1 image(s)	{"item_id": 96, "batch_id": 56, "batch_reference": "B-20260817-8DFACD"}	2026-08-17 10:38:15.386386+00	2026-08-17 10:38:15.386386+00
236	2	upload	72-SSC-7203	SAMPLE COOLER	Uploaded 1 image(s)	{"item_id": 97, "batch_id": 56, "batch_reference": "B-20260817-8DFACD"}	2026-08-17 10:38:15.386386+00	2026-08-17 10:38:15.386386+00
237	2	upload	73-BV-0023	VALVE,BALL	Uploaded 1 image(s)	{"item_id": 98, "batch_id": 56, "batch_reference": "B-20260817-8DFACD"}	2026-08-17 10:38:15.386386+00	2026-08-17 10:38:15.386386+00
238	2	extract	74-FG-024	GAUGE,SIGHT GLASS	Extracted from 1 photo(s)	{"cost_usd": 0.0, "input_tokens": 1838, "output_tokens": 505}	2026-08-17 10:40:57.038969+00	2026-08-17 10:40:57.038969+00
240	2	extract	71-FV-003	VALVE,CONTROL,FLOW	Extracted from 1 photo(s)	{"cost_usd": 0.0, "input_tokens": 1828, "output_tokens": 545}	2026-08-17 10:42:03.582937+00	2026-08-17 10:42:03.582937+00
247	2	login	\N	\N	Signed in	{}	2026-08-17 10:59:59.846897+00	2026-08-17 10:59:59.846897+00
250	2	login	\N	\N	Signed in	{}	2026-08-18 04:17:22.392806+00	2026-08-18 04:17:22.392806+00
255	2	download	12-4020-DBV-0004	DOUBLE BLOCK AND BLEED VALVE	Downloaded AI Output workbook	{}	2026-08-18 05:04:58.453308+00	2026-08-18 05:04:58.453308+00
261	2	duplicate_blocked	74-FG-024	GAUGE,SIGHT GLASS	Tag already extracted — existing record shown	{}	2026-08-18 05:19:14.36289+00	2026-08-18 05:19:14.36289+00
272	2	login	\N	\N	Signed in	{}	2026-08-18 06:25:55.021859+00	2026-08-18 06:25:55.021859+00
276	2	login	\N	\N	Signed in	{}	2026-08-18 08:29:27.912277+00	2026-08-18 08:29:27.912277+00
279	2	login	\N	\N	Signed in	{}	2026-08-18 08:51:40.019474+00	2026-08-18 08:51:40.019474+00
136	2	download	\N	\N	Downloaded consolidated Template workbook (21 tag(s))	{}	2026-08-12 11:27:21.928998+00	2026-08-12 11:27:21.928998+00
137	2	login	\N	\N	Signed in	{}	2026-08-12 11:31:30.760152+00	2026-08-12 11:31:30.760152+00
280	1	login	\N	\N	Signed in	{}	2026-08-18 08:52:24.619914+00	2026-08-18 08:52:24.619914+00
283	2	upload	22-GV-0550	VALVE,GATE	Uploaded 1 image(s)	{"item_id": 107, "batch_id": 65, "batch_reference": "B-20260818-042EA2"}	2026-08-18 09:01:35.152388+00	2026-08-18 09:01:35.152388+00
284	2	extract	22-GV-0550	VALVE,GATE	Extracted from 1 photo(s)	{"cost_usd": 0.029994, "input_tokens": 5853, "output_tokens": 829}	2026-08-18 09:01:47.170947+00	2026-08-18 09:01:47.170947+00
286	2	download	22-GV-0550	VALVE,GATE	Downloaded Template workbook	{}	2026-08-18 09:01:56.58593+00	2026-08-18 09:01:56.58593+00
290	1	login	\N	\N	Signed in	{}	2026-08-18 10:09:16.574997+00	2026-08-18 10:09:16.574997+00
143	2	login	\N	\N	Signed in	{}	2026-08-12 11:44:23.900115+00	2026-08-12 11:44:23.900115+00
144	2	login	\N	\N	Signed in	{}	2026-08-13 05:32:21.897583+00	2026-08-13 05:32:21.897583+00
145	2	login	\N	\N	Signed in	{}	2026-08-13 06:26:02.502057+00	2026-08-13 06:26:02.502057+00
146	2	login	\N	\N	Signed in	{}	2026-08-13 07:12:13.731588+00	2026-08-13 07:12:13.731588+00
147	2	login	\N	\N	Signed in	{}	2026-08-13 10:39:04.638682+00	2026-08-13 10:39:04.638682+00
148	2	login	\N	\N	Signed in	{}	2026-08-13 10:42:31.647369+00	2026-08-13 10:42:31.647369+00
149	2	login	\N	\N	Signed in	{}	2026-08-13 10:44:00.654911+00	2026-08-13 10:44:00.654911+00
150	2	login	\N	\N	Signed in	{}	2026-08-13 11:03:19.650219+00	2026-08-13 11:03:19.650219+00
151	2	login	\N	\N	Signed in	{}	2026-08-13 11:22:56.794357+00	2026-08-13 11:22:56.794357+00
297	2	login	\N	\N	Signed in	{}	2026-08-18 10:59:01.234296+00	2026-08-18 10:59:01.234296+00
299	2	login	\N	\N	Signed in	{}	2026-08-18 10:59:52.11262+00	2026-08-18 10:59:52.11262+00
154	2	download	\N	\N	Downloaded consolidated Template workbook (21 tag(s))	{}	2026-08-13 11:29:57.116798+00	2026-08-13 11:29:57.116798+00
300	4	login	\N	\N	Signed in	{}	2026-08-18 11:00:11.576691+00	2026-08-18 11:00:11.576691+00
301	4	duplicate_blocked	21-JDD-01	JUNCTION BOX,INSTRUMENT	Tag already extracted — existing record shown	{}	2026-08-18 11:00:30.65151+00	2026-08-18 11:00:30.65151+00
157	1	login	\N	\N	Signed in	{}	2026-08-13 11:45:46.59915+00	2026-08-13 11:45:46.59915+00
158	2	login	\N	\N	Signed in	{}	2026-08-13 11:47:24.045251+00	2026-08-13 11:47:24.045251+00
159	1	download	\N	\N	Downloaded consolidated Template workbook (22 tag(s))	{}	2026-08-14 04:14:26.592903+00	2026-08-14 04:14:26.592903+00
160	2	login	\N	\N	Signed in	{}	2026-08-14 04:16:43.05223+00	2026-08-14 04:16:43.05223+00
303	1	user_updated	\N	\N	Updated user user1	{}	2026-08-18 11:07:37.847166+00	2026-08-18 11:07:37.847166+00
305	3	login	\N	\N	Signed in	{}	2026-08-18 11:07:55.586171+00	2026-08-18 11:07:55.586171+00
163	1	login	\N	\N	Signed in	{}	2026-08-14 05:33:48.415351+00	2026-08-14 05:33:48.415351+00
164	2	login	\N	\N	Signed in	{}	2026-08-14 05:33:57.923052+00	2026-08-14 05:33:57.923052+00
306	1	login	\N	\N	Signed in	{}	2026-08-18 11:08:11.369876+00	2026-08-18 11:08:11.369876+00
308	2	login	\N	\N	Signed in	{}	2026-08-18 11:29:40.966963+00	2026-08-18 11:29:40.966963+00
309	1	login	\N	\N	Signed in	{}	2026-08-18 11:36:47.739875+00	2026-08-18 11:36:47.739875+00
168	2	login	\N	\N	Signed in	{}	2026-08-14 06:05:19.042784+00	2026-08-14 06:05:19.042784+00
169	2	download	\N	\N	Downloaded consolidated Template workbook (23 tag(s))	{}	2026-08-14 09:19:16.385706+00	2026-08-14 09:19:16.385706+00
170	1	login	\N	\N	Signed in	{}	2026-08-14 09:57:09.522655+00	2026-08-14 09:57:09.522655+00
171	1	login	\N	\N	Signed in	{}	2026-08-14 09:59:05.325237+00	2026-08-14 09:59:05.325237+00
172	1	login	\N	\N	Signed in	{}	2026-08-14 10:08:26.92592+00	2026-08-14 10:08:26.92592+00
310	2	login	\N	\N	Signed in	{}	2026-08-19 03:55:18.103334+00	2026-08-19 03:55:18.103334+00
322	2	upload	51-PT-701	TRANSMITTER,PRESSURE	Uploaded 1 image(s)	{"item_id": 115, "batch_id": 69, "batch_reference": "B-20260819-10430B"}	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:41.831303+00
327	2	upload	12-M2-PIT-0008	ELECTRONIC PRESSURE TRANSMITTER	Uploaded 3 image(s)	{"item_id": 117, "batch_id": 71, "batch_reference": "B-20260819-5295A7"}	2026-08-19 07:20:53.549498+00	2026-08-19 07:20:53.549498+00
328	2	extract	12-M2-PIT-0008	ELECTRONIC PRESSURE TRANSMITTER	Extracted from 3 photo(s)	{"cost_usd": 0.07611, "input_tokens": 13330, "output_tokens": 2408}	2026-08-19 07:21:22.055696+00	2026-08-19 07:21:22.055696+00
339	1	password_reset	\N	\N	Reset password for User1	{}	2026-08-19 08:18:56.176919+00	2026-08-19 08:18:56.176919+00
341	1	login	\N	\N	Signed in	{}	2026-08-19 08:19:37.672795+00	2026-08-19 08:19:37.672795+00
349	2	login	\N	\N	Signed in	{}	2026-08-19 09:18:10.082377+00	2026-08-19 09:18:10.082377+00
358	3	extract	12-4020-BV-0073	BALL VALVE	Extracted from 1 photo(s)	{"cost_usd": 0.029445, "input_tokens": 5855, "output_tokens": 792}	2026-08-19 09:42:35.554396+00	2026-08-19 09:42:35.554396+00
359	3	extract	12-4020-BV-0083	BALL VALVE	Extracted from 1 photo(s)	{"cost_usd": 0.036795, "input_tokens": 5855, "output_tokens": 1282}	2026-08-19 09:42:51.920968+00	2026-08-19 09:42:51.920968+00
360	3	download	\N	\N	Downloaded consolidated Template workbook (23 tag(s))	{}	2026-08-19 09:46:15.072916+00	2026-08-19 09:46:15.072916+00
364	3	login	\N	\N	Signed in	{}	2026-08-19 10:30:37.600888+00	2026-08-19 10:30:37.600888+00
367	2	duplicate_blocked	12-4020-BV-0074	VALVE,BALL	Tag already extracted — existing record shown	{}	2026-08-19 10:52:10.484461+00	2026-08-19 10:52:10.484461+00
371	3	download	12-GDF-03-0103	FLAMMABLE GAS DETECTOR	Downloaded Template workbook	{}	2026-08-19 11:13:41.262589+00	2026-08-19 11:13:41.262589+00
221	2	upload	12-4020-BV-0074	BALL VALVE	Uploaded 1 image(s)	{"item_id": 91, "batch_id": 54, "batch_reference": "B-20260817-263222"}	2026-08-17 10:01:52.693624+00	2026-08-17 10:01:52.693624+00
222	2	upload	12-4020-CC-0032	CORROSION COUPON	Uploaded 1 image(s)	{"item_id": 92, "batch_id": 54, "batch_reference": "B-20260817-263222"}	2026-08-17 10:01:52.693624+00	2026-08-17 10:01:52.693624+00
223	2	extract	12-4020-BV-0074	BALL VALVE	Extracted from 1 photo(s)	{"cost_usd": 0.0, "input_tokens": 1830, "output_tokens": 379}	2026-08-17 10:02:15.986022+00	2026-08-17 10:02:15.986022+00
228	2	upload	12-4020-CC-0032	CORROSION COUPON	Uploaded 1 image(s)	{"item_id": 93, "batch_id": 55, "batch_reference": "B-20260817-CF6061"}	2026-08-17 10:05:13.018397+00	2026-08-17 10:05:13.018397+00
241	2	extract	72-SSC-7203	SAMPLE COOLER	Extracted from 1 photo(s)	{"cost_usd": 0.0, "input_tokens": 1826, "output_tokens": 340}	2026-08-17 10:42:27.358846+00	2026-08-17 10:42:27.358846+00
242	2	extract	73-BV-0023	VALVE,BALL	Extracted from 1 photo(s)	{"cost_usd": 0.0, "input_tokens": 1863, "output_tokens": 479}	2026-08-17 10:43:43.87506+00	2026-08-17 10:43:43.87506+00
185	1	login	\N	\N	Signed in	{}	2026-08-14 11:14:13.087848+00	2026-08-14 11:14:13.087848+00
248	2	edit	73-BV-0023	VALVE,BALL	Saved revision 2	{}	2026-08-17 11:07:14.616661+00	2026-08-17 11:07:14.616661+00
251	2	login	\N	\N	Signed in	{}	2026-08-18 04:37:06.413956+00	2026-08-18 04:37:06.413956+00
256	2	upload	12-4021-TE-1001	TEMPERATURE ELEMENT	Uploaded 1 image(s)	{"item_id": 101, "batch_id": 59, "batch_reference": "B-20260818-B77D4B"}	2026-08-18 05:05:39.697362+00	2026-08-18 05:05:39.697362+00
257	2	extract	12-4021-TE-1001	TEMPERATURE ELEMENT	Extracted from 1 photo(s)	{"cost_usd": 0.041076, "input_tokens": 5862, "output_tokens": 1566}	2026-08-18 05:05:56.774816+00	2026-08-18 05:05:56.774816+00
190	1	download	\N	\N	Downloaded consolidated Template workbook (26 tag(s))	{}	2026-08-14 11:17:02.871984+00	2026-08-14 11:17:02.871984+00
191	1	user_updated	\N	\N	Updated user user1	{}	2026-08-14 11:20:28.758321+00	2026-08-14 11:20:28.758321+00
192	2	login	\N	\N	Signed in	{}	2026-08-14 11:37:05.605382+00	2026-08-14 11:37:05.605382+00
258	2	download	12-4021-TE-1001	TEMPERATURE ELEMENT	Downloaded AI Output workbook	{}	2026-08-18 05:06:02.687499+00	2026-08-18 05:06:02.687499+00
262	1	login	\N	\N	Signed in	{}	2026-08-18 05:53:26.258588+00	2026-08-18 05:53:26.258588+00
263	1	user_updated	\N	\N	Updated user User1	{}	2026-08-18 05:55:23.304899+00	2026-08-18 05:55:23.304899+00
196	2	login	\N	\N	Signed in	{}	2026-08-17 04:14:35.970038+00	2026-08-17 04:14:35.970038+00
197	2	login	\N	\N	Signed in	{}	2026-08-17 04:15:16.681092+00	2026-08-17 04:15:16.681092+00
198	2	download	\N	\N	Downloaded consolidated Template workbook (27 tag(s))	{}	2026-08-17 04:15:48.239007+00	2026-08-17 04:15:48.239007+00
266	1	user_updated	\N	\N	Updated user user1	{}	2026-08-18 05:55:58.456707+00	2026-08-18 05:55:58.456707+00
267	1	user_updated	\N	\N	Updated user user1	{}	2026-08-18 06:00:20.508882+00	2026-08-18 06:00:20.508882+00
273	2	upload	21-JDD-01	JUNCTION BOX,INSTRUMENT	Uploaded 1 image(s)	{"item_id": 105, "batch_id": 63, "batch_reference": "B-20260818-543192"}	2026-08-18 06:26:13.236281+00	2026-08-18 06:26:13.236281+00
277	2	duplicate_blocked	12-4021-TE-1001	TEMPERATURE ELEMENT	Tag already extracted — existing record shown	{}	2026-08-18 08:29:49.800829+00	2026-08-18 08:29:49.800829+00
203	2	login	\N	\N	Signed in	{}	2026-08-17 09:11:13.223212+00	2026-08-17 09:11:13.223212+00
204	4	login	\N	\N	Signed in	{}	2026-08-17 09:17:22.14256+00	2026-08-17 09:17:22.14256+00
205	4	login	\N	\N	Signed in	{}	2026-08-17 09:18:00.355924+00	2026-08-17 09:18:00.355924+00
206	1	login	\N	\N	Signed in	{}	2026-08-17 09:19:43.928173+00	2026-08-17 09:19:43.928173+00
207	2	login	\N	\N	Signed in	{}	2026-08-17 09:21:50.496247+00	2026-08-17 09:21:50.496247+00
208	2	login	\N	\N	Signed in	{}	2026-08-17 09:28:48.611557+00	2026-08-17 09:28:48.611557+00
285	2	download	22-GV-0550	VALVE,GATE	Downloaded AI Output workbook	{}	2026-08-18 09:01:55.282912+00	2026-08-18 09:01:55.282912+00
291	2	login	\N	\N	Signed in	{}	2026-08-18 10:11:56.85071+00	2026-08-18 10:11:56.85071+00
292	2	login	\N	\N	Signed in	{}	2026-08-18 10:12:36.570471+00	2026-08-18 10:12:36.570471+00
212	2	download	\N	\N	Downloaded consolidated Template workbook (29 tag(s))	{}	2026-08-17 09:31:16.136693+00	2026-08-17 09:31:16.136693+00
298	1	login	\N	\N	Signed in	{}	2026-08-18 10:59:27.872445+00	2026-08-18 10:59:27.872445+00
302	1	login	\N	\N	Signed in	{}	2026-08-18 11:07:28.321413+00	2026-08-18 11:07:28.321413+00
311	2	login	\N	\N	Signed in	{}	2026-08-19 05:03:13.147753+00	2026-08-19 05:03:13.147753+00
216	2	login	\N	\N	Signed in	{}	2026-08-17 09:42:59.396777+00	2026-08-17 09:42:59.396777+00
323	2	extract	22-GV-0553	VALVE,GATE	Extracted from 1 photo(s)	{"cost_usd": 0.030144, "input_tokens": 5853, "output_tokens": 839}	2026-08-19 07:04:53.473552+00	2026-08-19 07:04:53.473552+00
324	2	extract	22-LT-702	TRANSMITTER,LEVEL	Extracted from 1 photo(s)	{"cost_usd": 0.048294, "input_tokens": 5858, "output_tokens": 2048}	2026-08-19 07:05:16.891304+00	2026-08-19 07:05:16.891304+00
326	2	extract	51-PT-701	TRANSMITTER,PRESSURE	Extracted from 1 photo(s)	{"cost_usd": 0.020229, "input_tokens": 2538, "output_tokens": 841}	2026-08-19 07:08:40.524077+00	2026-08-19 07:08:40.524077+00
329	2	duplicate_blocked	21-JDD-01	JUNCTION BOX,INSTRUMENT	Tag already extracted — existing record shown	{}	2026-08-19 07:22:36.46058+00	2026-08-19 07:22:36.46058+00
330	2	login	\N	\N	Signed in	{}	2026-08-19 08:10:38.751695+00	2026-08-19 08:10:38.751695+00
332	2	download	\N	\N	Downloaded consolidated Template workbook (18 tag(s))	{}	2026-08-19 08:11:53.733573+00	2026-08-19 08:11:53.733573+00
333	2	duplicate_blocked	51-PT-701	TRANSMITTER,PRESSURE	Tag already extracted — existing record returned	{}	2026-08-19 08:15:01.838902+00	2026-08-19 08:15:01.838902+00
335	4	login	\N	\N	Signed in	{}	2026-08-19 08:17:28.084288+00	2026-08-19 08:17:28.084288+00
337	1	login	\N	\N	Signed in	{}	2026-08-19 08:18:27.864937+00	2026-08-19 08:18:27.864937+00
338	1	password_reset	\N	\N	Reset password for user1	{}	2026-08-19 08:18:46.626912+00	2026-08-19 08:18:46.626912+00
344	3	edit	21-JDD-01	JUNCTION BOX,INSTRUMENT	Saved revision 2	{}	2026-08-19 08:25:24.25938+00	2026-08-19 08:25:24.25938+00
345	3	download	21-JDD-01	JUNCTION BOX,INSTRUMENT	Downloaded AI Output workbook	{}	2026-08-19 08:25:33.162617+00	2026-08-19 08:25:33.162617+00
347	1	duplicate_blocked	12-4020-CC-0032	CORROSION COUPON	Tag already extracted — existing record returned	{}	2026-08-19 09:04:17.825083+00	2026-08-19 09:04:17.825083+00
350	3	upload	12-4020-BV	0073,BALL VALVE	Uploaded 2 image(s)	{"item_id": 120, "batch_id": 74, "batch_reference": "B-20260819-64218E"}	2026-08-19 09:23:15.477229+00	2026-08-19 09:23:15.477229+00
351	3	extract	12-4020-BV	0073,BALL VALVE	Extracted from 2 photo(s)	{"cost_usd": 0.079359, "input_tokens": 10608, "output_tokens": 3169}	2026-08-19 09:23:49.464594+00	2026-08-19 09:23:49.464594+00
354	3	extract	12-4020-FDI-21-0003	INFRARED FLAME DETECTOR	Extracted from 1 photo(s)	{"cost_usd": 0.055218, "input_tokens": 5866, "output_tokens": 2508}	2026-08-19 09:36:11.163132+00	2026-08-19 09:36:11.163132+00
355	3	extract	12-4020-NLV-0007	NEEDLE VALVE	Extracted from 2 photo(s)	{"cost_usd": 0.060384, "input_tokens": 10613, "output_tokens": 1903}	2026-08-19 09:36:34.540015+00	2026-08-19 09:36:34.540015+00
356	3	upload	12-4020-BV-0073	BALL VALVE	Uploaded 1 image(s)	{"item_id": 123, "batch_id": 76, "batch_reference": "B-20260819-80AECD"}	2026-08-19 09:42:24.863356+00	2026-08-19 09:42:24.863356+00
357	3	upload	12-4020-BV-0083	BALL VALVE	Uploaded 1 image(s)	{"item_id": 124, "batch_id": 76, "batch_reference": "B-20260819-80AECD"}	2026-08-19 09:42:24.863356+00	2026-08-19 09:42:24.863356+00
361	2	login	\N	\N	Signed in	{}	2026-08-19 09:56:19.123418+00	2026-08-19 09:56:19.123418+00
365	2	login	\N	\N	Signed in	{}	2026-08-19 10:51:07.732122+00	2026-08-19 10:51:07.732122+00
366	2	duplicate_blocked	12-4020-BV-0074	BALL VALVE	Tag already extracted — existing record shown	{}	2026-08-19 10:51:47.540984+00	2026-08-19 10:51:47.540984+00
369	3	upload	12-GDF-03-0103	FLAMMABLE GAS DETECTOR	Uploaded 2 image(s)	{"item_id": 128, "batch_id": 80, "batch_reference": "B-20260819-E8FCE5"}	2026-08-19 11:09:57.162819+00	2026-08-19 11:09:57.162819+00
373	3	upload	12-M2-GV-0038	GATE VALVE	Uploaded 1 image(s)	{"item_id": 130, "batch_id": 81, "batch_reference": "B-20260819-5F5B24"}	2026-08-19 11:15:23.201615+00	2026-08-19 11:15:23.201615+00
374	3	extract	12-M2-DBV-0002	DOUBLE BLOCK AND BLEED VALVE	Extracted from 2 photo(s)	{"cost_usd": 0.060087, "input_tokens": 10624, "output_tokens": 1881}	2026-08-19 11:15:45.845526+00	2026-08-19 11:15:45.845526+00
375	3	extract	12-M2-GV-0038	GATE VALVE	Extracted from 1 photo(s)	{"cost_usd": 0.03048, "input_tokens": 5855, "output_tokens": 861}	2026-08-19 11:15:56.892006+00	2026-08-19 11:15:56.892006+00
377	3	edit	12-M2-DBV-0002	DOUBLE BLOCK AND BLEED VALVE	Saved revision 2	{}	2026-08-19 11:18:42.429825+00	2026-08-19 11:18:42.429825+00
379	3	download	12-M2-GV-0038	GATE VALVE	Downloaded Template workbook	{}	2026-08-19 11:19:59.687926+00	2026-08-19 11:19:59.687926+00
380	3	download	12-M2-GV-0038	GATE VALVE	Downloaded Template workbook	{}	2026-08-19 11:23:50.951635+00	2026-08-19 11:23:50.951635+00
382	3	extract	12-M2-PIT-0001	PRESSURE TRANSMITTER	Extracted from 3 photo(s)	{"cost_usd": 0.074898, "input_tokens": 15371, "output_tokens": 1919}	2026-08-19 11:36:28.331076+00	2026-08-19 11:36:28.331076+00
378	3	download	12-M2-DBV-0002	DOUBLE BLOCK AND BLEED VALVE	Downloaded Template workbook	{}	2026-08-19 11:18:54.974371+00	2026-08-19 11:18:54.974371+00
381	3	upload	12-M2-PIT-0001	PRESSURE TRANSMITTER	Uploaded 3 image(s)	{"item_id": 131, "batch_id": 82, "batch_reference": "B-20260819-E833FC"}	2026-08-19 11:36:05.662009+00	2026-08-19 11:36:05.662009+00
383	2	duplicate_blocked	21-JDD-01	JUNCTION BOX,INSTRUMENT	Tag already extracted — existing record shown	{}	2026-08-19 11:39:08.952351+00	2026-08-19 11:39:08.952351+00
384	2	upload	12-M2-PIT	0008 ELECTRONIC PRESSURE TRANSMITTER	Uploaded 1 image(s)	{"item_id": 133, "batch_id": 83, "batch_reference": "B-20260819-461A32"}	2026-08-19 11:39:08.952351+00	2026-08-19 11:39:08.952351+00
385	3	edit	12-M2-PIT-0001	PRESSURE TRANSMITTER	Saved revision 2	{}	2026-08-19 11:39:17.002436+00	2026-08-19 11:39:17.002436+00
386	3	download	12-M2-PIT-0001	PRESSURE TRANSMITTER	Downloaded Template workbook	{}	2026-08-19 11:39:21.71825+00	2026-08-19 11:39:21.71825+00
387	2	extract	12-M2-PIT	0008 ELECTRONIC PRESSURE TRANSMITTER	Extracted from 1 photo(s)	{"cost_usd": 0.039063, "input_tokens": 3821, "output_tokens": 1840}	2026-08-19 11:39:29.029762+00	2026-08-19 11:39:29.029762+00
388	2	upload	12-M2-GV-0011	GATE VALVE	Uploaded 1 image(s)	{"item_id": 134, "batch_id": 84, "batch_reference": "B-20260819-62AA5C"}	2026-08-19 11:39:50.079227+00	2026-08-19 11:39:50.079227+00
389	2	extract	12-M2-GV-0011	GATE VALVE	Extracted from 1 photo(s)	{"cost_usd": 0.033015, "input_tokens": 5855, "output_tokens": 1030}	2026-08-19 11:40:02.218356+00	2026-08-19 11:40:02.218356+00
390	2	upload	22-LT	702 TRANSMITTER,LEVEL	Uploaded 1 image(s)	{"item_id": 135, "batch_id": 85, "batch_reference": "B-20260819-FD0A12"}	2026-08-19 11:40:50.249935+00	2026-08-19 11:40:50.249935+00
391	2	extract	22-LT	702 TRANSMITTER,LEVEL	Extracted from 1 photo(s)	{"cost_usd": 0.029511, "input_tokens": 5857, "output_tokens": 796}	2026-08-19 11:41:01.561988+00	2026-08-19 11:41:01.561988+00
392	2	duplicate_blocked	22-GV-0553	VALVE,GATE	Tag already extracted — existing record shown	{}	2026-08-19 11:42:02.663978+00	2026-08-19 11:42:02.663978+00
393	2	duplicate_blocked	22-GV-0550	VALVE,GATE	Tag already extracted — existing record shown	{}	2026-08-19 11:42:17.667056+00	2026-08-19 11:42:17.667056+00
394	3	upload	12-M2-PI-0002	PRESSURE GAUGE	Uploaded 3 image(s)	{"item_id": 138, "batch_id": 88, "batch_reference": "B-20260819-F58C90"}	2026-08-19 11:42:53.203688+00	2026-08-19 11:42:53.203688+00
395	3	extract	12-M2-PI-0002	PRESSURE GAUGE	Extracted from 3 photo(s)	{"cost_usd": 0.062916, "input_tokens": 15367, "output_tokens": 1121}	2026-08-19 11:43:10.614097+00	2026-08-19 11:43:10.614097+00
396	3	download	12-M2-PI-0002	PRESSURE GAUGE	Downloaded Template workbook	{}	2026-08-19 11:45:06.651626+00	2026-08-19 11:45:06.651626+00
397	3	duplicate_blocked	12-4020-FDI-21-0003	INFRARED FLAME DETECTOR	Tag already extracted — existing record shown	{}	2026-08-19 11:47:03.015804+00	2026-08-19 11:47:03.015804+00
398	3	upload	12-4020-BV-0111	BALL VALVE	Uploaded 2 image(s)	{"item_id": 140, "batch_id": 89, "batch_reference": "B-20260819-C2C95B"}	2026-08-19 11:47:03.015804+00	2026-08-19 11:47:03.015804+00
399	3	duplicate_blocked	12-4020-BV-0083	BALL VALVE	Tag already extracted — existing record shown	{}	2026-08-19 11:47:03.015804+00	2026-08-19 11:47:03.015804+00
400	3	download	12-4020-FDI-21-0003	INFRARED FLAME DETECTOR	Downloaded Template workbook	{}	2026-08-19 11:47:12.180795+00	2026-08-19 11:47:12.180795+00
401	3	extract	12-4020-BV-0111	BALL VALVE	Extracted from 2 photo(s)	{"cost_usd": 0.045432, "input_tokens": 10609, "output_tokens": 907}	2026-08-19 11:47:14.283894+00	2026-08-19 11:47:14.283894+00
402	3	download	12-4020-BV-0083	BALL VALVE	Downloaded Template workbook	{}	2026-08-19 11:48:17.1311+00	2026-08-19 11:48:17.1311+00
403	3	download	12-4020-BV-0111	BALL VALVE	Downloaded Template workbook	{}	2026-08-19 11:49:15.255287+00	2026-08-19 11:49:15.255287+00
404	3	download	12-4020-BV-0111	BALL VALVE	Downloaded Template workbook	{}	2026-08-19 11:49:39.348966+00	2026-08-19 11:49:39.348966+00
405	3	duplicate_blocked	12-4020-NLV-0007	NEEDLE VALVE	Tag already extracted — existing record shown	{}	2026-08-19 11:53:47.909541+00	2026-08-19 11:53:47.909541+00
406	2	upload	16-GV-1982	VALVE,GATE	Uploaded 1 image(s)	{"item_id": 143, "batch_id": 91, "batch_reference": "B-20260819-189961"}	2026-08-19 12:04:27.7187+00	2026-08-19 12:04:27.7187+00
407	2	upload	PM	8981B MOTOR,PUMP	Uploaded 1 image(s)	{"item_id": 144, "batch_id": 91, "batch_reference": "B-20260819-189961"}	2026-08-19 12:04:27.7187+00	2026-08-19 12:04:27.7187+00
408	2	extract	16-GV-1982	VALVE,GATE	Extracted from 1 photo(s)	{"cost_usd": 0.028614, "input_tokens": 5853, "output_tokens": 737}	2026-08-19 12:04:39.778652+00	2026-08-19 12:04:39.778652+00
409	2	extract	PM	8981B MOTOR,PUMP	Extracted from 1 photo(s)	{"cost_usd": 0.057528, "input_tokens": 5851, "output_tokens": 2665}	2026-08-19 12:05:08.597256+00	2026-08-19 12:05:08.597256+00
410	2	upload	20-DZT-006	TRANSMITTER,DENSITY	Uploaded 2 image(s)	{"item_id": 145, "batch_id": 92, "batch_reference": "B-20260819-4E7420"}	2026-08-19 12:10:13.626795+00	2026-08-19 12:10:13.626795+00
411	2	extract	20-DZT-006	TRANSMITTER,DENSITY	Extracted from 2 photo(s)	{"cost_usd": 0.053259, "input_tokens": 10613, "output_tokens": 1428}	2026-08-19 12:10:31.647575+00	2026-08-19 12:10:31.647575+00
412	2	login	\N	\N	Signed in	{}	2026-08-20 04:11:13.574744+00	2026-08-20 04:11:13.574744+00
413	1	login	\N	\N	Signed in	{}	2026-08-20 04:33:20.041889+00	2026-08-20 04:33:20.041889+00
414	1	login	\N	\N	Signed in	{}	2026-08-20 05:31:05.979319+00	2026-08-20 05:31:05.979319+00
415	1	login	\N	\N	Signed in	{}	2026-08-20 06:58:12.628236+00	2026-08-20 06:58:12.628236+00
416	1	download	\N	\N	Downloaded consolidated Template workbook (38 tag(s))	{}	2026-08-20 09:20:01.615119+00	2026-08-20 09:20:01.615119+00
417	2	download	\N	\N	Downloaded consolidated Template workbook (23 tag(s))	{}	2026-08-20 09:20:01.728383+00	2026-08-20 09:20:01.728383+00
418	3	download	\N	\N	Downloaded consolidated Template workbook (11 tag(s))	{}	2026-08-20 09:20:01.814786+00	2026-08-20 09:20:01.814786+00
419	4	download	\N	\N	Downloaded consolidated Template workbook (3 tag(s))	{}	2026-08-20 09:20:01.883877+00	2026-08-20 09:20:01.883877+00
420	1	download	\N	\N	Downloaded consolidated Template workbook (35 tag(s))	{}	2026-08-20 09:24:17.850373+00	2026-08-20 09:24:17.850373+00
421	2	login	\N	\N	Signed in	{}	2026-08-20 09:24:47.188348+00	2026-08-20 09:24:47.188348+00
422	2	download	\N	\N	Downloaded consolidated Template workbook (23 tag(s))	{}	2026-08-20 09:24:51.514507+00	2026-08-20 09:24:51.514507+00
423	2	download	\N	\N	Downloaded consolidated Template workbook (23 tag(s))	{}	2026-08-20 09:24:56.026536+00	2026-08-20 09:24:56.026536+00
424	3	login	\N	\N	Signed in	{}	2026-08-20 09:25:20.712601+00	2026-08-20 09:25:20.712601+00
425	3	download	\N	\N	Downloaded consolidated Template workbook (11 tag(s))	{}	2026-08-20 09:25:40.482576+00	2026-08-20 09:25:40.482576+00
426	3	login	\N	\N	Signed in	{}	2026-08-20 11:01:28.095765+00	2026-08-20 11:01:28.095765+00
427	3	download	\N	\N	Downloaded consolidated Template workbook (11 tag(s))	{}	2026-08-20 11:01:31.604308+00	2026-08-20 11:01:31.604308+00
428	3	login	\N	\N	Signed in	{}	2026-08-20 11:02:19.856338+00	2026-08-20 11:02:19.856338+00
429	3	login	\N	\N	Signed in	{}	2026-08-20 11:18:49.429885+00	2026-08-20 11:18:49.429885+00
430	3	upload	35-SFX-015	FIRE EXTINGUISHER,DCP,9KG	Uploaded 1 image(s)	{"item_id": 146, "batch_id": 93, "batch_reference": "B-20260820-18853E"}	2026-08-20 11:25:53.082352+00	2026-08-20 11:25:53.082352+00
431	3	upload	35-XL-01A-018	BEACON,FLASH,AMBER,24VDC	Uploaded 4 image(s)	{"item_id": 147, "batch_id": 93, "batch_reference": "B-20260820-18853E"}	2026-08-20 11:25:53.082352+00	2026-08-20 11:25:53.082352+00
432	3	extract	35-SFX-015	FIRE EXTINGUISHER,DCP,9KG	Extracted from 1 photo(s)	{"cost_usd": 0.031983, "input_tokens": 5866, "output_tokens": 959}	2026-08-20 11:26:05.313752+00	2026-08-20 11:26:05.313752+00
433	3	extract	35-XL-01A-018	BEACON,FLASH,AMBER,24VDC	Extracted from 4 photo(s)	{"cost_usd": 0.099189, "input_tokens": 20128, "output_tokens": 2587}	2026-08-20 11:26:32.986278+00	2026-08-20 11:26:32.986278+00
434	3	upload	16-NRV-1268	VALVE,CHECK,3INX300LBS	Uploaded 1 image(s)	{"item_id": 148, "batch_id": 94, "batch_reference": "B-20260820-02C1F9"}	2026-08-20 11:27:28.054792+00	2026-08-20 11:27:28.054792+00
435	3	upload	35-GDF-01A-007	DETECTOR,FLAMMABLE GAS,IR,0TO100%LEL	Uploaded 2 image(s)	{"item_id": 149, "batch_id": 94, "batch_reference": "B-20260820-02C1F9"}	2026-08-20 11:27:28.054792+00	2026-08-20 11:27:28.054792+00
451	3	download	\N	\N	Downloaded consolidated Template workbook (21 tag(s))	{}	2026-08-20 11:43:15.744737+00	2026-08-20 11:43:15.744737+00
436	3	extract	16-NRV-1268	VALVE,CHECK,3INX300LBS	Extracted from 1 photo(s)	{"cost_usd": 0.040239, "input_tokens": 5863, "output_tokens": 1510}	2026-08-20 11:27:45.354817+00	2026-08-20 11:27:45.354817+00
441	3	extract	72-PSV-003B	VALVE,PRESSURE SAFETY,3-X 4IN,SP29.5BAR	Extracted from 1 photo(s)	{"cost_usd": 0.032763, "input_tokens": 1426, "output_tokens": 1899}	2026-08-20 11:29:46.815028+00	2026-08-20 11:29:46.815028+00
443	3	extract	73-PV-029	VALVE,CONTROL,PRESSURE2IN	Extracted from 1 photo(s)	{"cost_usd": 0.032787, "input_tokens": 5884, "output_tokens": 1009}	2026-08-20 11:30:05.961083+00	2026-08-20 11:30:05.961083+00
437	3	extract	35-GDF-01A-007	DETECTOR,FLAMMABLE GAS,IR,0TO100%LEL	Extracted from 2 photo(s)	{"cost_usd": 0.050076, "input_tokens": 10632, "output_tokens": 1212}	2026-08-20 11:27:59.750715+00	2026-08-20 11:27:59.750715+00
450	3	extract	73-TV-208X	VALVE,CONTROL,TEMPERATURE,3IN	Extracted from 1 photo(s)	{"cost_usd": 0.048966, "input_tokens": 5847, "output_tokens": 2095}	2026-08-20 11:42:54.897116+00	2026-08-20 11:42:54.897116+00
438	3	upload	72-PSV-003B	VALVE,PRESSURE SAFETY,3-X 4IN,SP29.5BAR	Uploaded 1 image(s)	{"item_id": 150, "batch_id": 95, "batch_reference": "B-20260820-D1B169"}	2026-08-20 11:29:26.751146+00	2026-08-20 11:29:26.751146+00
439	3	upload	2196JAM-CSS	PUSH BUTTON STATION	Uploaded 1 image(s)	{"item_id": 151, "batch_id": 95, "batch_reference": "B-20260820-D1B169"}	2026-08-20 11:29:26.751146+00	2026-08-20 11:29:26.751146+00
440	3	upload	73-PV-029	VALVE,CONTROL,PRESSURE2IN	Uploaded 1 image(s)	{"item_id": 152, "batch_id": 95, "batch_reference": "B-20260820-D1B169"}	2026-08-20 11:29:26.751146+00	2026-08-20 11:29:26.751146+00
444	3	download	\N	\N	Downloaded consolidated Template workbook (18 tag(s))	{}	2026-08-20 11:33:23.72898+00	2026-08-20 11:33:23.72898+00
446	3	extract	16-LIT-357	TRANSMITTER,LEVEL,INDICATING,NCR	Extracted from 3 photo(s)	{"cost_usd": 0.063186, "input_tokens": 15377, "output_tokens": 1137}	2026-08-20 11:41:31.711668+00	2026-08-20 11:41:31.711668+00
442	3	extract	2196JAM-CSS	PUSH BUTTON STATION	Extracted from 1 photo(s)	{"cost_usd": 0.02505, "input_tokens": 4730, "output_tokens": 724}	2026-08-20 11:29:55.052797+00	2026-08-20 11:29:55.052797+00
445	3	upload	16-LIT-357	TRANSMITTER,LEVEL,INDICATING,NCR	Uploaded 3 image(s)	{"item_id": 153, "batch_id": 96, "batch_reference": "B-20260820-E14389"}	2026-08-20 11:41:12.796729+00	2026-08-20 11:41:12.796729+00
447	3	upload	72-LSL-102X	SWITCH,LEVEL	Uploaded 1 image(s)	{"item_id": 154, "batch_id": 97, "batch_reference": "B-20260820-747BD8"}	2026-08-20 11:42:06.473018+00	2026-08-20 11:42:06.473018+00
448	3	upload	73-TV-208X	VALVE,CONTROL,TEMPERATURE,3IN	Uploaded 1 image(s)	{"item_id": 155, "batch_id": 97, "batch_reference": "B-20260820-747BD8"}	2026-08-20 11:42:06.473018+00	2026-08-20 11:42:06.473018+00
449	3	extract	72-LSL-102X	SWITCH,LEVEL	Extracted from 1 photo(s)	{"cost_usd": 0.041457, "input_tokens": 1764, "output_tokens": 2411}	2026-08-20 11:42:32.484037+00	2026-08-20 11:42:32.484037+00
452	1	login	\N	\N	Signed in	{}	2026-08-20 12:12:35.028614+00	2026-08-20 12:12:35.028614+00
453	1	login	\N	\N	Signed in	{}	2026-08-21 05:20:23.511956+00	2026-08-21 05:20:23.511956+00
454	2	login	\N	\N	Signed in	{}	2026-08-21 05:21:12.936775+00	2026-08-21 05:21:12.936775+00
455	1	login	\N	\N	Signed in	{}	2026-08-21 05:23:04.412727+00	2026-08-21 05:23:04.412727+00
456	1	login	\N	\N	Signed in	{}	2026-08-21 05:54:03.173486+00	2026-08-21 05:54:03.173486+00
457	1	login	\N	\N	Signed in	{}	2026-08-21 09:12:32.03572+00	2026-08-21 09:12:32.03572+00
458	1	login	\N	\N	Signed in	{}	2026-08-21 09:13:01.718626+00	2026-08-21 09:13:01.718626+00
459	1	password_reset	\N	\N	Reset password for User1	{}	2026-08-21 09:13:28.469687+00	2026-08-21 09:13:28.469687+00
460	4	login	\N	\N	Signed in	{}	2026-08-21 09:13:42.262043+00	2026-08-21 09:13:42.262043+00
461	1	login	\N	\N	Signed in	{}	2026-08-21 09:17:33.862768+00	2026-08-21 09:17:33.862768+00
462	1	download	12-M2-PI-0002	PRESSURE GAUGE	Downloaded AI Output workbook	{}	2026-08-21 10:58:22.969623+00	2026-08-21 10:58:22.969623+00
463	1	login	\N	\N	Signed in	{}	2026-08-21 11:07:33.266545+00	2026-08-21 11:07:33.266545+00
464	1	login	\N	\N	Signed in	{}	2026-08-25 04:12:18.351941+00	2026-08-25 04:12:18.351941+00
465	1	user_updated	\N	\N	Updated user user1	{}	2026-08-25 04:35:10.187371+00	2026-08-25 04:35:10.187371+00
466	1	user_updated	\N	\N	Updated user user1	{}	2026-08-25 04:35:28.706977+00	2026-08-25 04:35:28.706977+00
467	1	user_updated	\N	\N	Updated user user1	{}	2026-08-25 04:35:30.979311+00	2026-08-25 04:35:30.979311+00
468	1	user_updated	\N	\N	Updated user user1	{}	2026-08-25 04:35:31.922779+00	2026-08-25 04:35:31.922779+00
469	1	user_updated	\N	\N	Updated user user1	{}	2026-08-25 04:35:33.949208+00	2026-08-25 04:35:33.949208+00
470	1	user_updated	\N	\N	Updated user user1	{}	2026-08-25 04:35:36.740028+00	2026-08-25 04:35:36.740028+00
471	1	login	\N	\N	Signed in	{}	2026-08-25 05:12:36.356999+00	2026-08-25 05:12:36.356999+00
472	1	download	\N	\N	Downloaded consolidated Template workbook (45 tag(s))	{}	2026-08-25 05:13:28.787564+00	2026-08-25 05:13:28.787564+00
473	1	login	\N	\N	Signed in	{}	2026-08-25 07:10:32.873288+00	2026-08-25 07:10:32.873288+00
474	1	login	\N	\N	Signed in	{}	2026-08-25 09:06:13.518473+00	2026-08-25 09:06:13.518473+00
475	2	login	\N	\N	Signed in	{}	2026-08-25 09:08:22.831287+00	2026-08-25 09:08:22.831287+00
476	1	login	\N	\N	Signed in	{}	2026-08-25 10:04:31.433307+00	2026-08-25 10:04:31.433307+00
477	1	login	\N	\N	Signed in	{}	2026-08-26 04:18:00.383613+00	2026-08-26 04:18:00.383613+00
478	1	login	\N	\N	Signed in	{}	2026-08-26 05:03:48.169371+00	2026-08-26 05:03:48.169371+00
479	1	login	\N	\N	Signed in	{}	2026-08-26 05:22:24.976565+00	2026-08-26 05:22:24.976565+00
480	1	login	\N	\N	Signed in	{}	2026-08-26 08:29:44.890895+00	2026-08-26 08:29:44.890895+00
481	1	login	\N	\N	Signed in	{}	2026-08-27 03:38:56.289399+00	2026-08-27 03:38:56.289399+00
482	1	login	\N	\N	Signed in	{}	2026-08-27 04:15:54.010321+00	2026-08-27 04:15:54.010321+00
483	1	login	\N	\N	Signed in	{}	2026-08-27 04:48:46.844962+00	2026-08-27 04:48:46.844962+00
484	3	login	\N	\N	Signed in	{}	2026-08-27 04:48:57.857606+00	2026-08-27 04:48:57.857606+00
485	3	download	73-TV-208X	VALVE,CONTROL,TEMPERATURE,3IN	Downloaded AI Output workbook	{}	2026-08-27 04:50:40.674896+00	2026-08-27 04:50:40.674896+00
486	3	download	\N	\N	Downloaded consolidated Template workbook (21 tag(s))	{}	2026-08-27 04:51:09.87245+00	2026-08-27 04:51:09.87245+00
487	3	download	2196JAM-CSS	PUSH BUTTON STATION	Downloaded AI Output workbook	{}	2026-08-27 04:57:45.002033+00	2026-08-27 04:57:45.002033+00
488	3	download	72-LSL-102X	SWITCH,LEVEL	Downloaded AI Output workbook	{}	2026-08-27 04:58:29.896555+00	2026-08-27 04:58:29.896555+00
489	3	download	16-LIT-357	TRANSMITTER,LEVEL,INDICATING,NCR	Downloaded AI Output workbook	{}	2026-08-27 04:59:06.954133+00	2026-08-27 04:59:06.954133+00
490	3	download	73-PV-029	VALVE,CONTROL,PRESSURE2IN	Downloaded AI Output workbook	{}	2026-08-27 04:59:52.651361+00	2026-08-27 04:59:52.651361+00
491	3	download	72-PSV-003B	VALVE,PRESSURE SAFETY,3-X 4IN,SP29.5BAR	Downloaded AI Output workbook	{}	2026-08-27 05:00:11.906305+00	2026-08-27 05:00:11.906305+00
492	3	download	35-GDF-01A-007	DETECTOR,FLAMMABLE GAS,IR,0TO100%LEL	Downloaded AI Output workbook	{}	2026-08-27 05:00:43.047687+00	2026-08-27 05:00:43.047687+00
493	3	download	16-NRV-1268	VALVE,CHECK,3INX300LBS	Downloaded AI Output workbook	{}	2026-08-27 05:03:10.555353+00	2026-08-27 05:03:10.555353+00
494	3	download	35-XL-01A-018	BEACON,FLASH,AMBER,24VDC	Downloaded AI Output workbook	{}	2026-08-27 05:03:53.943473+00	2026-08-27 05:03:53.943473+00
495	3	download	35-SFX-015	FIRE EXTINGUISHER,DCP,9KG	Downloaded AI Output workbook	{}	2026-08-27 05:04:15.544968+00	2026-08-27 05:04:15.544968+00
496	3	download	12-4020-BV-0111	BALL VALVE	Downloaded AI Output workbook	{}	2026-08-27 05:04:51.306153+00	2026-08-27 05:04:51.306153+00
497	3	download	12-4020-BV-0083	BALL VALVE	Downloaded AI Output workbook	{}	2026-08-27 05:06:16.525298+00	2026-08-27 05:06:16.525298+00
498	3	download	12-M2-PI-0002	PRESSURE GAUGE	Downloaded AI Output workbook	{}	2026-08-27 05:06:37.85162+00	2026-08-27 05:06:37.85162+00
499	3	download	12-M2-PIT-0001	PRESSURE TRANSMITTER	Downloaded AI Output workbook	{}	2026-08-27 05:07:05.332427+00	2026-08-27 05:07:05.332427+00
500	3	download	12-M2-GV-0038	GATE VALVE	Downloaded AI Output workbook	{}	2026-08-27 05:09:10.562219+00	2026-08-27 05:09:10.562219+00
501	3	download	12-M2-DBV-0002	DOUBLE BLOCK AND BLEED VALVE	Downloaded AI Output workbook	{}	2026-08-27 05:09:28.448382+00	2026-08-27 05:09:28.448382+00
502	3	download	12-GDF-03-0103	FLAMMABLE GAS DETECTOR	Downloaded AI Output workbook	{}	2026-08-27 05:09:51.884943+00	2026-08-27 05:09:51.884943+00
503	3	download	12-4020-FDI-21-0003	INFRARED FLAME DETECTOR	Downloaded AI Output workbook	{}	2026-08-27 05:10:24.382096+00	2026-08-27 05:10:24.382096+00
504	3	download	12-4020-BV-0073	BALL VALVE	Downloaded AI Output workbook	{}	2026-08-27 05:11:02.394775+00	2026-08-27 05:11:02.394775+00
505	3	download	12-4020-NLV-0007	NEEDLE VALVE	Downloaded AI Output workbook	{}	2026-08-27 05:11:58.467745+00	2026-08-27 05:11:58.467745+00
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: visioncore
--

COPY public.alembic_version (version_num) FROM stdin;
0004
\.


--
-- Data for Name: api_usage; Type: TABLE DATA; Schema: public; Owner: visioncore
--

COPY public.api_usage (id, user_id, tag_number, model, input_tokens, output_tokens, cost_usd, latency_ms, success, error_message, created_at, updated_at) FROM stdin;
1	1	54-038-P12	claude-sonnet-5	0	0	0	0	f	Claude API error (401): Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}, 'request_id': 'req_011CdoHsvAvvFDyxCsPq3P1Q'}	2026-08-07 11:15:10.373007+00	2026-08-07 11:15:10.373007+00
2	1	51-PT-701	claude-sonnet-5	0	0	0	0	f	Claude API error (401): Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}, 'request_id': 'req_011CdoHtAXsfnLXJLj56J3ef'}	2026-08-07 11:15:13.453737+00	2026-08-07 11:15:13.453737+00
3	1	12-M2-PIT-0008	claude-sonnet-5	0	0	0	0	f	Claude API error (502): <html>\r\n<head><title>502 Bad Gateway</title></head>\r\n<body>\r\n<center><h1>502 Bad Gateway</h1></center>\r\n<hr><center>cloudflare</center>\r\n</body>\r\n</html>	2026-08-07 11:15:16.10224+00	2026-08-07 11:15:16.10224+00
4	1	12-4021-TIT-1001	claude-sonnet-5	0	0	0	0	f	Claude API error (401): Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}, 'request_id': 'req_011CdoHtZorNeLFXt6oDaTvM'}	2026-08-07 11:15:18.972498+00	2026-08-07 11:15:18.972498+00
5	1	12-4020-DBV-0004	claude-sonnet-5	0	0	0	0	f	Claude API error (401): Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}, 'request_id': 'req_011CdoHthXgzTWzpH4Hp1P6R'}	2026-08-07 11:15:20.690624+00	2026-08-07 11:15:20.690624+00
6	1	74-FG-024	claude-sonnet-5	0	0	0	0	f	Claude API error (401): Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}, 'request_id': 'req_011CdvXFk3srkM8f5xaKzFU3'}	2026-08-11 06:54:44.374688+00	2026-08-11 06:54:44.374688+00
7	1	21-JDD-01	claude-sonnet-5	0	0	0	0	f	Could not reach the Claude API: Connection error.	2026-08-11 06:54:47.338076+00	2026-08-11 06:54:47.338076+00
8	1	22-LT-702	claude-sonnet-5	0	0	0	0	f	Could not reach the Claude API: Connection error.	2026-08-11 06:54:50.263502+00	2026-08-11 06:54:50.263502+00
9	1	22-GV-0553	claude-sonnet-5	0	0	0	0	f	Claude API error (502): <html>\r\n<head><title>502 Bad Gateway</title></head>\r\n<body>\r\n<center><h1>502 Bad Gateway</h1></center>\r\n<hr><center>cloudflare</center>\r\n</body>\r\n</html>	2026-08-11 06:54:53.19804+00	2026-08-11 06:54:53.19804+00
10	1	71-FV-003	claude-sonnet-5	0	0	0	0	f	Claude API error (401): Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}, 'request_id': 'req_011CdvXGWAyR6abAp7BcY6Hh'}	2026-08-11 06:54:55.092692+00	2026-08-11 06:54:55.092692+00
11	2	12-4021-TE-1001	claude-sonnet-5	0	0	0	0	f	Claude API error (401): Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}, 'request_id': 'req_011CdvdwvQ37fbNEzjaM7cdy'}	2026-08-11 08:22:30.638594+00	2026-08-11 08:22:30.638594+00
12	2	12-M2-GV-0011	claude-sonnet-5	0	0	0	0	f	Could not reach the Claude API: Connection error.	2026-08-11 08:27:11.679252+00	2026-08-11 08:27:11.679252+00
13	2	54-038-P12	claude-sonnet-5	0	0	0	0	f	ANTHROPIC_API_KEY is not set. Add it to .env and restart the API.	2026-08-11 08:43:04.705949+00	2026-08-11 08:43:04.705949+00
14	2	12-4020-DBV-0004	claude-sonnet-5	0	0	0	0	f	ANTHROPIC_API_KEY is not set. Add it to .env and restart the API.	2026-08-11 09:15:16.73592+00	2026-08-11 09:15:16.73592+00
89	2	20-DZT-006	claude-sonnet-5	10613	1428	0.053259	17957	t	\N	2026-08-19 12:10:31.641426+00	2026-08-19 12:10:31.641426+00
53	2	12-4020-BV-0074	gemini-3.6-flash	1830	379	0	23249	t	\N	2026-08-17 10:02:15.980685+00	2026-08-17 10:02:15.980685+00
54	2	12-4020-CC-0032	gemini-3.6-flash	0	0	0	0	f	Gemini API error: UNAVAILABLE. This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.	2026-08-17 10:03:31.526292+00	2026-08-17 10:03:31.526292+00
55	2	12-4020-CC-0032	gemini-3.6-flash	1833	470	0	37453	t	\N	2026-08-17 10:05:50.500357+00	2026-08-17 10:05:50.500357+00
56	2	74-FG-024	gemini-3.6-flash	1838	505	0	161597	t	\N	2026-08-17 10:40:57.034576+00	2026-08-17 10:40:57.034576+00
57	2	54-038-P12	gemini-3.6-flash	1858	393	0	54606	t	\N	2026-08-17 10:41:51.677909+00	2026-08-17 10:41:51.677909+00
58	2	71-FV-003	gemini-3.6-flash	1828	545	0	11865	t	\N	2026-08-17 10:42:03.577404+00	2026-08-17 10:42:03.577404+00
59	2	72-SSC-7203	gemini-3.6-flash	1826	340	0	23739	t	\N	2026-08-17 10:42:27.351648+00	2026-08-17 10:42:27.351648+00
60	2	73-BV-0023	gemini-3.6-flash	1863	479	0	76475	t	\N	2026-08-17 10:43:43.869706+00	2026-08-17 10:43:43.869706+00
61	2	12	gemini-3.6-flash	1830	385	0	84040	t	\N	2026-08-17 10:59:02.347033+00	2026-08-17 10:59:02.347033+00
62	2	12-4020-DBV-0004	claude-sonnet-5	3821	1128	0.028383000000000002	13491	t	\N	2026-08-18 04:56:44.364993+00	2026-08-18 04:56:44.364993+00
63	2	12-4021-TE-1001	claude-sonnet-5	5862	1566	0.041076	17001	t	\N	2026-08-18 05:05:56.767373+00	2026-08-18 05:05:56.767373+00
64	2	12-4020-FE-0031	claude-sonnet-5	5858	782	0.029304	9866	t	\N	2026-08-18 06:08:35.257843+00	2026-08-18 06:08:35.257843+00
65	2	21-JDD-01	claude-sonnet-5	5863	733	0.028584000000000002	10265	t	\N	2026-08-18 06:26:23.580215+00	2026-08-18 06:26:23.580215+00
66	2	22-GV-0550	claude-sonnet-5	5853	829	0.029994	11936	t	\N	2026-08-18 09:01:47.163889+00	2026-08-18 09:01:47.163889+00
67	1	12-ECP-0002	claude-sonnet-5	5862	1311	0.037251000000000006	15517	t	\N	2026-08-19 05:43:01.833477+00	2026-08-19 05:43:01.833477+00
68	2	22-GV-0553	claude-sonnet-5	5853	839	0.030143999999999997	11561	t	\N	2026-08-19 07:04:53.469563+00	2026-08-19 07:04:53.469563+00
69	2	22-LT-702	claude-sonnet-5	5858	2048	0.048294	23379	t	\N	2026-08-19 07:05:16.884692+00	2026-08-19 07:05:16.884692+00
70	2	51-PT-701	claude-sonnet-5	0	0	0	0	f	Could not parse Claude's JSON: Expecting ',' delimiter: line 1 column 2062 (char 2061)	2026-08-19 07:05:27.390283+00	2026-08-19 07:05:27.390283+00
71	2	51-PT-701	claude-sonnet-5	2538	841	0.020228999999999997	9743	t	\N	2026-08-19 07:08:40.51739+00	2026-08-19 07:08:40.51739+00
72	2	12-M2-PIT-0008	claude-sonnet-5	13330	2408	0.07611	28434	t	\N	2026-08-19 07:21:22.043929+00	2026-08-19 07:21:22.043929+00
73	3	12-4020-BV	claude-sonnet-5	10608	3169	0.079359	33866	t	\N	2026-08-19 09:23:49.458336+00	2026-08-19 09:23:49.458336+00
74	3	12-4020-FDI-21-0003	claude-sonnet-5	5866	2508	0.055218	28392	t	\N	2026-08-19 09:36:11.157736+00	2026-08-19 09:36:11.157736+00
75	3	12-4020-NLV-0007	claude-sonnet-5	10613	1903	0.060384	23330	t	\N	2026-08-19 09:36:34.530601+00	2026-08-19 09:36:34.530601+00
76	3	12-4020-BV-0073	claude-sonnet-5	5855	792	0.029445	10647	t	\N	2026-08-19 09:42:35.548718+00	2026-08-19 09:42:35.548718+00
77	3	12-4020-BV-0083	claude-sonnet-5	5855	1282	0.036795	16334	t	\N	2026-08-19 09:42:51.916041+00	2026-08-19 09:42:51.916041+00
78	3	12-GDF-03-0103	claude-sonnet-5	10619	2086	0.06314700000000001	22935	t	\N	2026-08-19 11:10:20.179076+00	2026-08-19 11:10:20.179076+00
79	3	12-M2-DBV-0002	claude-sonnet-5	10624	1881	0.060087	22593	t	\N	2026-08-19 11:15:45.838483+00	2026-08-19 11:15:45.838483+00
80	3	12-M2-GV-0038	claude-sonnet-5	5855	861	0.03048	11006	t	\N	2026-08-19 11:15:56.885233+00	2026-08-19 11:15:56.885233+00
81	3	12-M2-PIT-0001	claude-sonnet-5	15371	1919	0.07489799999999999	22618	t	\N	2026-08-19 11:36:28.327563+00	2026-08-19 11:36:28.327563+00
82	2	12-M2-PIT	claude-sonnet-5	3821	1840	0.039063	19965	t	\N	2026-08-19 11:39:29.02206+00	2026-08-19 11:39:29.02206+00
83	2	12-M2-GV-0011	claude-sonnet-5	5855	1030	0.033015	12083	t	\N	2026-08-19 11:40:02.208099+00	2026-08-19 11:40:02.208099+00
84	2	22-LT	claude-sonnet-5	5857	796	0.029511000000000003	11260	t	\N	2026-08-19 11:41:01.557549+00	2026-08-19 11:41:01.557549+00
85	3	12-M2-PI-0002	claude-sonnet-5	15367	1121	0.062916	17338	t	\N	2026-08-19 11:43:10.60414+00	2026-08-19 11:43:10.60414+00
86	3	12-4020-BV-0111	claude-sonnet-5	10609	907	0.045432	11202	t	\N	2026-08-19 11:47:14.27485+00	2026-08-19 11:47:14.27485+00
87	2	16-GV-1982	claude-sonnet-5	5853	737	0.028614	11964	t	\N	2026-08-19 12:04:39.772105+00	2026-08-19 12:04:39.772105+00
88	2	PM	claude-sonnet-5	5851	2665	0.057527999999999996	28778	t	\N	2026-08-19 12:05:08.592838+00	2026-08-19 12:05:08.592838+00
90	3	35-SFX-015	claude-sonnet-5	5866	959	0.031983	12156	t	\N	2026-08-20 11:26:05.30816+00	2026-08-20 11:26:05.30816+00
91	3	35-XL-01A-018	claude-sonnet-5	20128	2587	0.099189	27629	t	\N	2026-08-20 11:26:32.97939+00	2026-08-20 11:26:32.97939+00
92	3	16-NRV-1268	claude-sonnet-5	5863	1510	0.040239	17229	t	\N	2026-08-20 11:27:45.348646+00	2026-08-20 11:27:45.348646+00
93	3	35-GDF-01A-007	claude-sonnet-5	10632	1212	0.050075999999999996	14361	t	\N	2026-08-20 11:27:59.745969+00	2026-08-20 11:27:59.745969+00
94	3	72-PSV-003B	claude-sonnet-5	1426	1899	0.032763	20013	t	\N	2026-08-20 11:29:46.809642+00	2026-08-20 11:29:46.809642+00
95	3	2196JAM-CSS	claude-sonnet-5	4730	724	0.02505	8204	t	\N	2026-08-20 11:29:55.046308+00	2026-08-20 11:29:55.046308+00
96	3	73-PV-029	claude-sonnet-5	5884	1009	0.032787	10876	t	\N	2026-08-20 11:30:05.955802+00	2026-08-20 11:30:05.955802+00
97	3	16-LIT-357	claude-sonnet-5	15377	1137	0.06318599999999999	18844	t	\N	2026-08-20 11:41:31.704+00	2026-08-20 11:41:31.704+00
98	3	72-LSL-102X	claude-sonnet-5	1764	2411	0.041457	25975	t	\N	2026-08-20 11:42:32.477417+00	2026-08-20 11:42:32.477417+00
99	3	73-TV-208X	claude-sonnet-5	5847	2095	0.048966	22379	t	\N	2026-08-20 11:42:54.89189+00	2026-08-20 11:42:54.89189+00
\.


--
-- Data for Name: asset_tags; Type: TABLE DATA; Schema: public; Owner: visioncore
--

COPY public.asset_tags (id, tag_number, description, ai_payload, final_payload, ai_excel_path, template_excel_path, edited_by_id, created_by_id, revision, created_at, updated_at) FROM stdin;
38	12-4020-DBV-0004	DOUBLE BLOCK AND BLEED VALVE	{"fields": {"make": {"value": "ASTEC VALVES & FITTINGS", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "778558.990.1M", "quality": "Verify"}, "serial_no": {"value": "DC1857", "quality": "Confirmed"}, "tag_number": {"value": "12-4020-DBV-0004", "quality": "Confirmed"}, "description": {"value": "DOUBLE BLOCK AND BLEED VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\" ASME 1500#", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "02", "quality": "Confirmed"}, "additional_information": {"value": "CUSTOMER: AXIOM INTERNATIONAL W.L.L., PO. NO.: PO-ASTEC-SO-6371-AK-74587, VALVE TYPE: INTEGRAL DOUBLE BLOCK & BLEED VALVE, VALVE BORE: 10 MM, BODY MOC (NACE): ASTM A182 GR. F316, TRIM MOC (NACE): ASTM A182 GR. F316, SEAT MOC: PEEK, DESIGN PRESSURE: 248.2 BARG @ 38 °C, DESIGN TEMPERATURE: -50 °C TO 150 °C, HYDRO (SHELL): 372.5 BARG, HYDRO (SEAT): 273.5 BARG, PNEU (SEAT): 7 BARG, HEAT NO.: A-9596, MESC NO.: 778558.990.1M, DESIGN CODE: ASME B16.34 / ISO 17292 / EEMUA 182, HEAT TREATMENT: SOLUTION ANNEALED", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "No tag number is printed on the nameplate itself; register value 12-4020-DBV-0004 used as instructed. Date of manufacturing printed as '02-2025' — interpreted as month 02, year 2025. MESC No. used as part number reference since no explicit 'Part No.' field is printed. No country of origin or hazardous area classification marking visible on either plate photo.", "qc_comment": "Both nameplate photos are clear and well-lit with legible text; minor glare present on second plate but does not obscure key data.", "photo_status": "EASY"}	{"fields": {"make": {"value": "ASTEC VALVES & FITTINGS", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "778558.990.1M", "quality": "Verify"}, "serial_no": {"value": "DC1857", "quality": "Confirmed"}, "tag_number": {"value": "12-4020-DBV-0004", "quality": "Confirmed"}, "description": {"value": "DOUBLE BLOCK AND BLEED VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\" ASME 1500#", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "02", "quality": "Confirmed"}, "additional_information": {"value": "CUSTOMER: AXIOM INTERNATIONAL W.L.L., PO. NO.: PO-ASTEC-SO-6371-AK-74587, VALVE TYPE: INTEGRAL DOUBLE BLOCK & BLEED VALVE, VALVE BORE: 10 MM, BODY MOC (NACE): ASTM A182 GR. F316, TRIM MOC (NACE): ASTM A182 GR. F316, SEAT MOC: PEEK, DESIGN PRESSURE: 248.2 BARG @ 38 °C, DESIGN TEMPERATURE: -50 °C TO 150 °C, HYDRO (SHELL): 372.5 BARG, HYDRO (SEAT): 273.5 BARG, PNEU (SEAT): 7 BARG, HEAT NO.: A-9596, MESC NO.: 778558.990.1M, DESIGN CODE: ASME B16.34 / ISO 17292 / EEMUA 182, HEAT TREATMENT: SOLUTION ANNEALED", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "No tag number is printed on the nameplate itself; register value 12-4020-DBV-0004 used as instructed. Date of manufacturing printed as '02-2025' — interpreted as month 02, year 2025. MESC No. used as part number reference since no explicit 'Part No.' field is printed. No country of origin or hazardous area classification marking visible on either plate photo.", "qc_comment": "Both nameplate photos are clear and well-lit with legible text; minor glare present on second plate but does not obscure key data.", "photo_status": "EASY"}	/data/storage/exports/12-4020-DBV-0004/AI Output-12-4020-DBV-0004-DOUBLE BLOCK AND BLEED VALVE.xlsx	/data/storage/exports/12-4020-DBV-0004/12-4020-DBV-0004-DOUBLE BLOCK AND BLEED VALVE-Template.xlsx	\N	2	1	2026-08-18 04:56:44.374848+00	2026-08-18 04:56:44.374848+00
42	22-GV-0550	VALVE,GATE	{"fields": {"make": {"value": "KJS KOOKJAE KOREA", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "KOREA", "quality": "Confirmed"}, "part_no": {"value": "LVGAD0002", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "22-GV-0550", "quality": "Confirmed"}, "description": {"value": "VALVE,GATE", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "STANDARD: ANSI B16.34, CLASS: 150 (partially obscured, could be 300), BODY/TRIM MATERIAL: WCB / CR13 / CR13, PRESSURE RATING: 285 PSI AT 100°F, TAG-LIKE CODE: LVGA (partially obscured), UPPER PLATE CODES (inverted, partially legible): LVGAD0002, DA06L, DA01L", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Plate is heavily corroded, glared, and partially obscured by a wire loop and rust, making several fields (class rating, additional upper plate tag) uncertain. Upper inverted plate shows codes resembling 'LVGAD0002', 'DA06L', 'DA01L' which do not match the register tag 22-GV-0550 - flagged as possible mismatch or unrelated component tag, not a definitive nameplate serial. No size, model, serial, weight, or hazardous area classification printed or legible on this plate.", "qc_comment": "Recommend re-photographing the plate in better light and without wire obstruction to confirm CLASS rating and verify the upper inverted plate codes against the asset register.", "photo_status": "HARD"}	{"fields": {"make": {"value": "KJS KOOKJAE KOREA", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "KOREA", "quality": "Confirmed"}, "part_no": {"value": "LVGAD0002", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "22-GV-0550", "quality": "Confirmed"}, "description": {"value": "VALVE,GATE", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "STANDARD: ANSI B16.34, CLASS: 150 (partially obscured, could be 300), BODY/TRIM MATERIAL: WCB / CR13 / CR13, PRESSURE RATING: 285 PSI AT 100°F, TAG-LIKE CODE: LVGA (partially obscured), UPPER PLATE CODES (inverted, partially legible): LVGAD0002, DA06L, DA01L", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Plate is heavily corroded, glared, and partially obscured by a wire loop and rust, making several fields (class rating, additional upper plate tag) uncertain. Upper inverted plate shows codes resembling 'LVGAD0002', 'DA06L', 'DA01L' which do not match the register tag 22-GV-0550 - flagged as possible mismatch or unrelated component tag, not a definitive nameplate serial. No size, model, serial, weight, or hazardous area classification printed or legible on this plate.", "qc_comment": "Recommend re-photographing the plate in better light and without wire obstruction to confirm CLASS rating and verify the upper inverted plate codes against the asset register.", "photo_status": "HARD"}	/data/storage/exports/22-GV-0550/AI Output-22-GV-0550-VALVE,GATE.xlsx	/data/storage/exports/22-GV-0550/22-GV-0550-VALVE,GATE-Template.xlsx	\N	2	1	2026-08-18 09:01:47.170947+00	2026-08-18 09:01:47.170947+00
43	12-ECP-0002	ELECTRIC CONTROL PANEL	{"fields": {"make": {"value": "R. STAHL", "quality": "Confirmed"}, "model": {"value": "8146/5083", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "GERMANY", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "12-ECP-0002", "quality": "Confirmed"}, "description": {"value": "ELECTRIC CONTROL PANEL", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2017", "quality": "Confirmed"}, "month_of_manufacture": {"value": "07", "quality": "Confirmed"}, "additional_information": {"value": "TYPE: CONTROL BOX, STANDARD: IEC 61439-2, INGRESS PROTECTION: IP66, TEMP CLASS: T5 Ta -50°C....+55°C, SUPPLY VOLTAGE: 230 V, CABLE CSA: 2,5 mm², CURRENT: 6 A, FREQUENCY: 50/60 Hz, ORDER NO.: 2010283791/70, BARCODE: 1714704380440000, MANUFACTURER ADDRESS: HQ R. STAHL, D-74638 Waldenburg, www.stahl-ex.com, MADE IN: Germany", "quality": "Confirmed"}, "hazardous_classification": {"value": "PTB 01 ATEX 1024, II 2 G Ex db eb IIC T5 Gb, II 2 D Ex tb IIIC T95°C Db, IECEx PTB 06.0090, Ex db eb IIC T5 Gb, Ex tb IIIC T95°C Db, CE 0158", "quality": "Confirmed"}}, "remarks": "Plate itself shows a longer tag '12-4020-ECP-0002' on the upper metal strip, differing from the register tag '12-ECP-0002' — register value retained as instructed, mismatch flagged for verification. Serial number and part number are not separately printed on the main data plate (only order/date codes present). Size/dimension and weight are not indicated anywhere on the plate.", "qc_comment": "Main data plate is clear and well-lit; upper tag strip has minor corrosion spots but text is legible. No serial number field found, so it was marked not present. Recommend field verification of the printed long tag number against asset register.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "R. STAHL", "quality": "Confirmed"}, "model": {"value": "8146/5083", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "GERMANY", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "12-ECP-0002", "quality": "Confirmed"}, "description": {"value": "ELECTRIC CONTROL PANEL", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2017", "quality": "Confirmed"}, "month_of_manufacture": {"value": "07", "quality": "Confirmed"}, "additional_information": {"value": "TYPE: CONTROL BOX, STANDARD: IEC 61439-2, INGRESS PROTECTION: IP66, TEMP CLASS: T5 Ta -50°C....+55°C, SUPPLY VOLTAGE: 230 V, CABLE CSA: 2,5 mm², CURRENT: 6 A, FREQUENCY: 50/60 Hz, ORDER NO.: 2010283791/70, BARCODE: 1714704380440000, MANUFACTURER ADDRESS: HQ R. STAHL, D-74638 Waldenburg, www.stahl-ex.com, MADE IN: Germany", "quality": "Confirmed"}, "hazardous_classification": {"value": "PTB 01 ATEX 1024, II 2 G Ex db eb IIC T5 Gb, II 2 D Ex tb IIIC T95°C Db, IECEx PTB 06.0090, Ex db eb IIC T5 Gb, Ex tb IIIC T95°C Db, CE 0158", "quality": "Confirmed"}}, "remarks": "Plate itself shows a longer tag '12-4020-ECP-0002' on the upper metal strip, differing from the register tag '12-ECP-0002' — register value retained as instructed, mismatch flagged for verification. Serial number and part number are not separately printed on the main data plate (only order/date codes present). Size/dimension and weight are not indicated anywhere on the plate.", "qc_comment": "Main data plate is clear and well-lit; upper tag strip has minor corrosion spots but text is legible. No serial number field found, so it was marked not present. Recommend field verification of the printed long tag number against asset register.", "photo_status": "MEDIUM"}	/data/storage/exports/12-ECP-0002/AI Output-12-ECP-0002-ELECTRIC CONTROL PANEL.xlsx	/data/storage/exports/12-ECP-0002/12-ECP-0002-ELECTRIC CONTROL PANEL-Template.xlsx	\N	1	1	2026-08-19 05:43:01.841406+00	2026-08-19 05:43:01.841406+00
59	22-LT	702 TRANSMITTER,LEVEL	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "200 LBS", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "SP2-058", "quality": "Verify"}, "serial_no": {"value": "MSR-13071-1", "quality": "Verify"}, "tag_number": {"value": "22-LT", "quality": "Confirmed"}, "description": {"value": "702 TRANSMITTER,LEVEL", "quality": "Confirmed"}, "size_dimension": {"value": "1.5 IN", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "TORQUE TUBE MAT'L: INCONEL(?), CHAMBER MAT'L: SS(?), DISPLACER MAT'L: (illegible), DISP COLLAPSING PRESS AT 60F (CALC): 1200(?), MIN OUTPUT MA: 4-20 MA, DISP VOL: 56.56 CU.IN, LENGTH: 813 MM / 24 IN(?)", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate is heavily worn, rusted, and glare-affected making many values partially legible. Serial number, part number, weight, and material fields are best-effort readings and should be verified in person. No manufacturer, model, country, or date-of-manufacture markings were visible on the plate. Tag number and description confirmed from asset register match the visual context (22-LT-702 stenciled fragment visible as '-702' on plate, consistent with register).", "qc_comment": "Close-up angle and corrosion obscure several data fields; recommend physical re-inspection or a clearer photo with better lighting to confirm serial no., part no., and material specifications.", "photo_status": "HARD"}	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "200 LBS", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "SP2-058", "quality": "Verify"}, "serial_no": {"value": "MSR-13071-1", "quality": "Verify"}, "tag_number": {"value": "22-LT", "quality": "Confirmed"}, "description": {"value": "702 TRANSMITTER,LEVEL", "quality": "Confirmed"}, "size_dimension": {"value": "1.5 IN", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "TORQUE TUBE MAT'L: INCONEL(?), CHAMBER MAT'L: SS(?), DISPLACER MAT'L: (illegible), DISP COLLAPSING PRESS AT 60F (CALC): 1200(?), MIN OUTPUT MA: 4-20 MA, DISP VOL: 56.56 CU.IN, LENGTH: 813 MM / 24 IN(?)", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate is heavily worn, rusted, and glare-affected making many values partially legible. Serial number, part number, weight, and material fields are best-effort readings and should be verified in person. No manufacturer, model, country, or date-of-manufacture markings were visible on the plate. Tag number and description confirmed from asset register match the visual context (22-LT-702 stenciled fragment visible as '-702' on plate, consistent with register).", "qc_comment": "Close-up angle and corrosion obscure several data fields; recommend physical re-inspection or a clearer photo with better lighting to confirm serial no., part no., and material specifications.", "photo_status": "HARD"}	/data/storage/exports/22-LT/AI Output-22-LT-702 TRANSMITTER,LEVEL.xlsx	/data/storage/exports/22-LT/22-LT-702 TRANSMITTER,LEVEL-Template.xlsx	\N	2	1	2026-08-19 11:41:01.561988+00	2026-08-19 11:41:01.561988+00
39	12-4021-TE-1001	TEMPERATURE ELEMENT	{"fields": {"make": {"value": "ROSEMOUNT", "quality": "Confirmed"}, "model": {"value": "214CRTSMA1D3M0270SLK1UAE 190M2XA", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "USA", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "25SHTP0332906", "quality": "Confirmed"}, "tag_number": {"value": "12-4021-TE-1001", "quality": "Confirmed"}, "description": {"value": "TEMPERATURE ELEMENT", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2025", "quality": "Verify"}, "month_of_manufacture": {"value": "05", "quality": "Verify"}, "additional_information": {"value": "SENSOR: PT100, RANGE: -50 to 450°C, DATE CODE: 05/25, CAL. DATE: 23-Jul-2025, CAL. DUE: 23-Jul-2026, CAL. BY: Febin Xavier, CERT. NO.: 07-25-25SHTC0195161, CALIBRATION STICKER SR/TAG NO.: 25SHTC0195161, CALIBRATED BY: PROMPT Engineering & Trading Services Co. W.L.L (TEL: +974-4418757, FAX: +974-4418969), ASSEMBLED IN: USA, SECOND ROSEMOUNT PLATE VISIBLE BELOW (partially obscured, details illegible)", "quality": "Verify"}, "hazardous_classification": {"value": "CE marked; FM approval diamond symbol present but certificate text illegible/obscured", "quality": "Verify"}}, "remarks": "The printed 'TAG' on the Rosemount label (12-4021-TE-1001) matches the register tag number, confirmed. A separate calibration sticker shows an unrelated 'Sr./Tag No.' (25SHTC0195161) and a different SN (25SHTP0332906) appears on the main nameplate — these are likely different identifiers (calibration cert vs. sensor serial) and should be verified against records. A second Rosemount nameplate is visible at the bottom of the photo but is largely obscured by wiring and glare; its details (hazardous area certification, ratings) could not be read and should be checked physically. Date code '05/25' interpreted as May 2025 manufacture date per rule 5.", "qc_comment": "Primary Rosemount nameplate (model, SN, sensor type, range, tag) is clearly legible. Calibration sticker text is mostly clear except a smudged line near 'Cal. By'. The lower secondary nameplate with hazardous area certification details is obscured by wiring/glare and could not be transcribed confidently — recommend re-photographing that plate directly for full ATEX/FM marking verification.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "ROSEMOUNT", "quality": "Confirmed"}, "model": {"value": "214CRTSMA1D3M0270SLK1UAE 190M2XA", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "United States of America", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "25SHTP0332906", "quality": "Confirmed"}, "tag_number": {"value": "12-4021-TE-1001", "quality": "Confirmed"}, "description": {"value": "TEMPERATURE ELEMENT", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2025", "quality": "Verify"}, "month_of_manufacture": {"value": "05", "quality": "Verify"}, "additional_information": {"value": "SENSOR: PT100, RANGE: -50 to 450°C, DATE CODE: 05/25, CAL. DATE: 23-Jul-2025, CAL. DUE: 23-Jul-2026, CAL. BY: Febin Xavier, CERT. NO.: 07-25-25SHTC0195161, CALIBRATION STICKER SR/TAG NO.: 25SHTC0195161, CALIBRATED BY: PROMPT Engineering & Trading Services Co. W.L.L (TEL: +974-4418757, FAX: +974-4418969), ASSEMBLED IN: USA, SECOND ROSEMOUNT PLATE VISIBLE BELOW (partially obscured, details illegible)", "quality": "Verify"}, "hazardous_classification": {"value": "CE marked; FM approval diamond symbol present but certificate text illegible/obscured", "quality": "Verify"}}, "remarks": "The printed 'TAG' on the Rosemount label (12-4021-TE-1001) matches the register tag number, confirmed. A separate calibration sticker shows an unrelated 'Sr./Tag No.' (25SHTC0195161) and a different SN (25SHTP0332906) appears on the main nameplate — these are likely different identifiers (calibration cert vs. sensor serial) and should be verified against records. A second Rosemount nameplate is visible at the bottom of the photo but is largely obscured by wiring and glare; its details (hazardous area certification, ratings) could not be read and should be checked physically. Date code '05/25' interpreted as May 2025 manufacture date per rule 5.", "qc_comment": "Primary Rosemount nameplate (model, SN, sensor type, range, tag) is clearly legible. Calibration sticker text is mostly clear except a smudged line near 'Cal. By'. The lower secondary nameplate with hazardous area certification details is obscured by wiring/glare and could not be transcribed confidently — recommend re-photographing that plate directly for full ATEX/FM marking verification.", "photo_status": "MEDIUM"}	/data/storage/exports/12-4021-TE-1001/AI Output-12-4021-TE-1001-TEMPERATURE ELEMENT.xlsx	/data/storage/exports/12-4021-TE-1001/12-4021-TE-1001-TEMPERATURE ELEMENT-Template.xlsx	2	2	2	2026-08-18 05:05:56.774816+00	2026-08-18 08:31:00.276281+00
44	22-GV-0553	VALVE,GATE	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "KOREA", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "LVGAA1000", "quality": "Verify"}, "tag_number": {"value": "22-GV-0553", "quality": "Confirmed"}, "description": {"value": "VALVE,GATE", "quality": "Confirmed"}, "size_dimension": {"value": "2\\"", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "STANDARD: ANSI B16.34, CLASS: 150, BODY/TRIM: WCB / CR13 / CR13 / HF, PRESSURE_RATING: 285 PSI AT 100°F, LOCATION_TEXT: (DOK)JAE KOREA (partially legible manufacturer city)", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate heavily caked with dust/mud obscuring the manufacturer name (only partial letters '...KJS' and '...OKJAE KOREA' visible), making make/model illegible. Serial/heat code 'LVGAAM000' or 'LVGAAT000' is unclear due to wear - transcribed best-effort as 'LVGAA1000', quality Verify. No tag number is printed on the plate itself; register value 22-GV-0553 used as instructed. Size shown as '2\\"' but partially worn.", "qc_comment": "Plate is a valve body pressure/material rating tag, not a full nameplate - fields like make, model, serial, weight, year/month, and hazardous classification are not typically present on this type of tag and are heavily obscured by dirt/corrosion. Recommend physical cleaning and re-photographing for confirmation of manufacturer and serial/heat number.", "photo_status": "HARD"}	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "KOREA", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "LVGAA1000", "quality": "Verify"}, "tag_number": {"value": "22-GV-0553", "quality": "Confirmed"}, "description": {"value": "VALVE,GATE", "quality": "Confirmed"}, "size_dimension": {"value": "2\\"", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "STANDARD: ANSI B16.34, CLASS: 150, BODY/TRIM: WCB / CR13 / CR13 / HF, PRESSURE_RATING: 285 PSI AT 100°F, LOCATION_TEXT: (DOK)JAE KOREA (partially legible manufacturer city)", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate heavily caked with dust/mud obscuring the manufacturer name (only partial letters '...KJS' and '...OKJAE KOREA' visible), making make/model illegible. Serial/heat code 'LVGAAM000' or 'LVGAAT000' is unclear due to wear - transcribed best-effort as 'LVGAA1000', quality Verify. No tag number is printed on the plate itself; register value 22-GV-0553 used as instructed. Size shown as '2\\"' but partially worn.", "qc_comment": "Plate is a valve body pressure/material rating tag, not a full nameplate - fields like make, model, serial, weight, year/month, and hazardous classification are not typically present on this type of tag and are heavily obscured by dirt/corrosion. Recommend physical cleaning and re-photographing for confirmation of manufacturer and serial/heat number.", "photo_status": "HARD"}	/data/storage/exports/22-GV-0553/AI Output-22-GV-0553-VALVE,GATE.xlsx	/data/storage/exports/22-GV-0553/22-GV-0553-VALVE,GATE-Template.xlsx	\N	2	1	2026-08-19 07:04:53.473552+00	2026-08-19 07:04:53.473552+00
40	12-4020-FE-0031	FLOW ELEMENT	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "405CS030N040D3P1QC1Q8Q76J5E5139", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "00-370001-219 REV. AB", "quality": "Confirmed"}, "serial_no": {"value": "25DUFB0000130", "quality": "Confirmed"}, "tag_number": {"value": "12-4020-FE-0031", "quality": "Confirmed"}, "description": {"value": "FLOW ELEMENT", "quality": "Confirmed"}, "size_dimension": {"value": "3 INCHES", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "06", "quality": "Confirmed"}, "additional_information": {"value": "CUSTOMER TAG: 12-4020-FIT-0031, CALIBRATION FACTOR: 0.558, METER BETA: .30 BETA, PRESSURE/TEMP LIMITATIONS: 600# ANSI, PN100, 316SS, MAX TEMP: 450 DEG F, DATE: 06/25", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Plate's own 'Customer Tag' reads 12-4020-FIT-0031, not matching the register tag 12-4020-FE-0031 or asset description 'FLOW ELEMENT' (plate appears to be for a flow transmitter/FIT, not a flow element). Register values retained per instructions but mismatch should be verified. Manufacturer name/logo not visible on plate. Country of origin not printed.", "qc_comment": "Text is largely legible but plate is angled and reflective in places; tag number discrepancy (FIT vs FE) is the key item requiring human verification.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "405CS030N040D3P1QC1Q8Q76J5E5139", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "00-370001-219 REV. AB", "quality": "Confirmed"}, "serial_no": {"value": "25DUFB0000130", "quality": "Confirmed"}, "tag_number": {"value": "12-4020-FE-0031", "quality": "Confirmed"}, "description": {"value": "FLOW ELEMENT", "quality": "Confirmed"}, "size_dimension": {"value": "3 INCHES", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "06", "quality": "Confirmed"}, "additional_information": {"value": "CUSTOMER TAG: 12-4020-FIT-0031, CALIBRATION FACTOR: 0.558, METER BETA: .30 BETA, PRESSURE/TEMP LIMITATIONS: 600# ANSI, PN100, 316SS, MAX TEMP: 450 DEG F, DATE: 06/25", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Plate's own 'Customer Tag' reads 12-4020-FIT-0031, not matching the register tag 12-4020-FE-0031 or asset description 'FLOW ELEMENT' (plate appears to be for a flow transmitter/FIT, not a flow element). Register values retained per instructions but mismatch should be verified. Manufacturer name/logo not visible on plate. Country of origin not printed.", "qc_comment": "Text is largely legible but plate is angled and reflective in places; tag number discrepancy (FIT vs FE) is the key item requiring human verification.", "photo_status": "MEDIUM"}	/data/storage/exports/12-4020-FE-0031/AI Output-12-4020-FE-0031-FLOW ELEMENT.xlsx	/data/storage/exports/12-4020-FE-0031/12-4020-FE-0031-FLOW ELEMENT-Template.xlsx	\N	2	1	2026-08-18 06:08:35.264838+00	2026-08-18 06:08:35.264838+00
31	12-4020-CC-0032	CORROSION COUPON	{"fields": {"make": {"value": "RCSL LTD", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "12-4020-CC-0032", "quality": "Confirmed"}, "description": {"value": "CORROSION COUPON", "quality": "Confirmed"}, "size_dimension": {"value": "2\\" FLAREWELD", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "04", "quality": "Confirmed"}, "additional_information": {"value": "Accessory Type: Coupon Holder", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Manufacture date recorded as April 2025 (04/2025).", "qc_comment": "Nameplate clearly legible and fully transcribed.", "photo_status": "EASY"}	{"fields": {"make": {"value": "RCSL LTD", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "12-4020-CC-0032", "quality": "Confirmed"}, "description": {"value": "CORROSION COUPON", "quality": "Confirmed"}, "size_dimension": {"value": "2\\" FLAREWELD", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "04", "quality": "Confirmed"}, "additional_information": {"value": "Accessory Type: Coupon Holder", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Manufacture date recorded as April 2025 (04/2025).", "qc_comment": "Nameplate clearly legible and fully transcribed.", "photo_status": "EASY"}	/data/storage/exports/12-4020-CC-0032/AI Output-12-4020-CC-0032-CORROSION COUPON.xlsx	/data/storage/exports/12-4020-CC-0032/12-4020-CC-0032-CORROSION COUPON-Template.xlsx	\N	2	1	2026-08-17 10:05:50.505095+00	2026-08-17 10:05:50.505095+00
37	12	IJBF-1067-FIRE AND GAS JUNCTION BOX	{"fields": {"make": {"value": "EATON", "quality": "Confirmed"}, "model": {"value": "Ex-Cell-T S3 505020", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "GERMANY", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "PET00165-24", "quality": "Confirmed"}, "tag_number": {"value": "12", "quality": "Confirmed"}, "description": {"value": "IJBF-1067-FIRE AND GAS JUNCTION BOX", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2024", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "VOLTAGE Ue: 690V, MANUFACTURER: COOPER CROUSE-HINDS GmbH, D-69412 EBERBACH, GERMANY, WARNING: DO NOT OPEN WHEN ENERGISED", "quality": "Confirmed"}, "hazardous_classification": {"value": "II 2G Ex eb IIC T5 Gb, II 2D Ex tb IIIC T95 °C Db, Tamb: -20 °C to +55 °C, BVS 16 ATEX E 115X, IECEx BVS 16.0080X, IP66", "quality": "Confirmed"}}, "remarks": "Year of manufacture (2024) inferred from serial number suffix '-24'.", "qc_comment": "Nameplate is clear and fully legible.", "photo_status": "EASY"}	{"fields": {"make": {"value": "EATON", "quality": "Confirmed"}, "model": {"value": "Ex-Cell-T S3 505020", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "GERMANY", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "PET00165-24", "quality": "Confirmed"}, "tag_number": {"value": "12", "quality": "Confirmed"}, "description": {"value": "IJBF-1067-FIRE AND GAS JUNCTION BOX", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2024", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "VOLTAGE Ue: 690V, MANUFACTURER: COOPER CROUSE-HINDS GmbH, D-69412 EBERBACH, GERMANY, WARNING: DO NOT OPEN WHEN ENERGISED", "quality": "Confirmed"}, "hazardous_classification": {"value": "II 2G Ex eb IIC T5 Gb, II 2D Ex tb IIIC T95 °C Db, Tamb: -20 °C to +55 °C, BVS 16 ATEX E 115X, IECEx BVS 16.0080X, IP66", "quality": "Confirmed"}}, "remarks": "Year of manufacture (2024) inferred from serial number suffix '-24'.", "qc_comment": "Nameplate is clear and fully legible.", "photo_status": "EASY"}	/data/storage/exports/12/AI Output-12-IJBF-1067-FIRE AND GAS JUNCTION BOX.xlsx	/data/storage/exports/12/12-IJBF-1067-FIRE AND GAS JUNCTION BOX-Template.xlsx	\N	2	1	2026-08-17 10:59:02.35202+00	2026-08-17 10:59:02.35202+00
60	12-M2-PI-0002	PRESSURE GAUGE	{"fields": {"make": {"value": "General Gauges Bourdon", "quality": "Confirmed"}, "model": {"value": "LFBSPG-V", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "2408860485", "quality": "Confirmed"}, "tag_number": {"value": "12-M2-PI-0002", "quality": "Confirmed"}, "description": {"value": "PRESSURE GAUGE", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "STANDARD: EN 837-1, ACCURACY CLASS: 1%, WETTED PART MATERIAL: MONEL, RANGE: 0-360 PSI(G) / 0-25 BAR(G), CASE MATERIAL: SS 316, CAL TAG REF NO: 2408860485, CAL DATE: 08-Nov-2025, CAL DUE: 08-Nov-2026, CAL BY: Febin Xavier, CERT NO: 11-25-2408860485, CALIBRATION SERVICE PROVIDER: PROMPT Engineering & Trading Services Co WLL, TEL: +974 4441057, ADDITIONAL LABEL CODE: LFBSPG-V", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Tag number on both the mounting bracket plate and calibration tag matches the register (12-M2-PI-0002). Gauge dial shows manufacturer 'General Gauges Bourdon', class 1% Monel movement, EN 837-1 standard, dual scale 0-360 psi(g)/0-25 bar(g); no serial, model, weight, country, or manufacture date printed on the dial itself. A separate stainless calibration tag (Photo 3) gives serial no. 2408860485, calibration dates, and a code 'LFBSPG-V' which may be an internal model/reference code rather than a manufacturer model number - please verify. The back of the gauge (Photo 2) shows only 'SS 316' stamped, indicating case material, no other data visible. No hazardous area (ATEX/IECEx) marking is visible on the gauge.", "qc_comment": "Dial face is clear and legible; calibration tag text is glare-affected and at an angle, some digits (e.g., serial prefix, cert no.) inferred with reasonable confidence. No manufacturer plate with model/serial in traditional format was found separate from the calibration sticker; recommend field verification of 'LFBSPG-V' as model code and confirmation of country/year of manufacture from purchase records.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "General Gauges Bourdon", "quality": "Confirmed"}, "model": {"value": "LFBSPG-V", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "2408860485", "quality": "Confirmed"}, "tag_number": {"value": "12-M2-PI-0002", "quality": "Confirmed"}, "description": {"value": "PRESSURE GAUGE", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "STANDARD: EN 837-1, ACCURACY CLASS: 1%, WETTED PART MATERIAL: MONEL, RANGE: 0-360 PSI(G) / 0-25 BAR(G), CASE MATERIAL: SS 316, CAL TAG REF NO: 2408860485, CAL DATE: 08-Nov-2025, CAL DUE: 08-Nov-2026, CAL BY: Febin Xavier, CERT NO: 11-25-2408860485, CALIBRATION SERVICE PROVIDER: PROMPT Engineering & Trading Services Co WLL, TEL: +974 4441057, ADDITIONAL LABEL CODE: LFBSPG-V", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Tag number on both the mounting bracket plate and calibration tag matches the register (12-M2-PI-0002). Gauge dial shows manufacturer 'General Gauges Bourdon', class 1% Monel movement, EN 837-1 standard, dual scale 0-360 psi(g)/0-25 bar(g); no serial, model, weight, country, or manufacture date printed on the dial itself. A separate stainless calibration tag (Photo 3) gives serial no. 2408860485, calibration dates, and a code 'LFBSPG-V' which may be an internal model/reference code rather than a manufacturer model number - please verify. The back of the gauge (Photo 2) shows only 'SS 316' stamped, indicating case material, no other data visible. No hazardous area (ATEX/IECEx) marking is visible on the gauge.", "qc_comment": "Dial face is clear and legible; calibration tag text is glare-affected and at an angle, some digits (e.g., serial prefix, cert no.) inferred with reasonable confidence. No manufacturer plate with model/serial in traditional format was found separate from the calibration sticker; recommend field verification of 'LFBSPG-V' as model code and confirmation of country/year of manufacture from purchase records.", "photo_status": "MEDIUM"}	/data/storage/exports/12-M2-PI-0002/AI Output-12-M2-PI-0002-PRESSURE GAUGE.xlsx	/data/storage/exports/12-M2-PI-0002/12-M2-PI-0002-PRESSURE GAUGE-Template.xlsx	\N	3	1	2026-08-19 11:43:10.614097+00	2026-08-19 11:43:10.614097+00
45	22-LT-702	TRANSMITTER,LEVEL	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "500 LBS", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "MSP-13071-...(partially legible)", "quality": "Verify"}, "tag_number": {"value": "22-LT-702", "quality": "Confirmed"}, "description": {"value": "TRANSMITTER,LEVEL", "quality": "Confirmed"}, "size_dimension": {"value": "1.5 IN", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "DISP SIZE: 1.5 IN, MIN: 2 IN, OUTPUT: 4-20 MA, DISP COLLAPSING PRESS AT 60F (CALC): approx. 1200 (partially legible), DISPLACER VOLUME: 56.56 CU IN, LENGTH: 813 MM, TORQUE TUBE MAT'L: INCONEL (partially legible), CHAMBER MAT'L: CS (partially legible), DISPLACER MAT'L: SS (partially legible)", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate heavily worn, glared, and partially corroded; many fields (manufacturer, model, part no., country, date codes, hazardous area rating) are illegible or absent. Serial number and collapsing pressure values are only partially visible due to glare and rust. A fragment reading '-LT-702' matches the register tag 22-LT-702, but full context could not be confirmed due to obstruction by mounting hardware.", "qc_comment": "Recommend physical re-inspection or cleaning of plate to confirm manufacturer, model, serial number, and material codes before finalizing asset register entry.", "photo_status": "HARD"}	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "500 LBS", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "MSP-13071-...(partially legible)", "quality": "Verify"}, "tag_number": {"value": "22-LT-702", "quality": "Confirmed"}, "description": {"value": "TRANSMITTER,LEVEL", "quality": "Confirmed"}, "size_dimension": {"value": "1.5 IN", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "DISP SIZE: 1.5 IN, MIN: 2 IN, OUTPUT: 4-20 MA, DISP COLLAPSING PRESS AT 60F (CALC): approx. 1200 (partially legible), DISPLACER VOLUME: 56.56 CU IN, LENGTH: 813 MM, TORQUE TUBE MAT'L: INCONEL (partially legible), CHAMBER MAT'L: CS (partially legible), DISPLACER MAT'L: SS (partially legible)", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate heavily worn, glared, and partially corroded; many fields (manufacturer, model, part no., country, date codes, hazardous area rating) are illegible or absent. Serial number and collapsing pressure values are only partially visible due to glare and rust. A fragment reading '-LT-702' matches the register tag 22-LT-702, but full context could not be confirmed due to obstruction by mounting hardware.", "qc_comment": "Recommend physical re-inspection or cleaning of plate to confirm manufacturer, model, serial number, and material codes before finalizing asset register entry.", "photo_status": "HARD"}	/data/storage/exports/22-LT-702/AI Output-22-LT-702-TRANSMITTER,LEVEL.xlsx	/data/storage/exports/22-LT-702/22-LT-702-TRANSMITTER,LEVEL-Template.xlsx	\N	2	1	2026-08-19 07:05:16.891304+00	2026-08-19 07:05:16.891304+00
46	51-PT-701	TRANSMITTER,PRESSURE	{"fields": {"make": {"value": "YOKOGAWA", "quality": "Confirmed"}, "model": {"value": "EJX 430A", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "EAS5G-9190B", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "51-PT-701", "quality": "Confirmed"}, "description": {"value": "TRANSMITTER,PRESSURE", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "TRANSMITTER: DPharp, MODEL: EJX 430A, SUFFIX: EAS5G-9190B, PRESSURE RATING: 12 bar (partially legible), MISC NUMBER: 526, PARTIAL CODE: 22261... (obscured), LOGO: I.A. Safety marking present but details illegible", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate is heavily worn, dirty, and partially obscured by mounting screw and dust, limiting legibility. Model and suffix codes read directly but suffix has some ambiguity due to corrosion. Pressure rating '12 bar' and a numeric code '526' are visible on second plate but context is unclear. Serial number, part number distinct from suffix, weight, country of origin, manufacture date, and hazardous area classification are not legible or not visibly printed. Tag number and description were supplied by asset register and match expected equipment type (pressure transmitter); no conflicting tag was visible on the plate itself.", "qc_comment": "Recommend physical re-inspection or higher-resolution photos to confirm serial number, hazardous area rating, and full suffix code; current transcription relies on partial visibility of corroded plate.", "photo_status": "HARD"}	{"fields": {"make": {"value": "YOKOGAWA", "quality": "Confirmed"}, "model": {"value": "EJX 430A", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "EAS5G-9190B", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "51-PT-701", "quality": "Confirmed"}, "description": {"value": "TRANSMITTER,PRESSURE", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "TRANSMITTER: DPharp, MODEL: EJX 430A, SUFFIX: EAS5G-9190B, PRESSURE RATING: 12 bar (partially legible), MISC NUMBER: 526, PARTIAL CODE: 22261... (obscured), LOGO: I.A. Safety marking present but details illegible", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate is heavily worn, dirty, and partially obscured by mounting screw and dust, limiting legibility. Model and suffix codes read directly but suffix has some ambiguity due to corrosion. Pressure rating '12 bar' and a numeric code '526' are visible on second plate but context is unclear. Serial number, part number distinct from suffix, weight, country of origin, manufacture date, and hazardous area classification are not legible or not visibly printed. Tag number and description were supplied by asset register and match expected equipment type (pressure transmitter); no conflicting tag was visible on the plate itself.", "qc_comment": "Recommend physical re-inspection or higher-resolution photos to confirm serial number, hazardous area rating, and full suffix code; current transcription relies on partial visibility of corroded plate.", "photo_status": "HARD"}	/data/storage/exports/51-PT-701/AI Output-51-PT-701-TRANSMITTER,PRESSURE.xlsx	/data/storage/exports/51-PT-701/51-PT-701-TRANSMITTER,PRESSURE-Template.xlsx	\N	2	1	2026-08-19 07:08:40.524077+00	2026-08-19 07:08:40.524077+00
76	72-LSL-102X	SWITCH,LEVEL	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "915-P22A-010/9D1-1221-02", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "569789-01-001", "quality": "Verify"}, "tag_number": {"value": "72-LSL-102X", "quality": "Confirmed"}, "description": {"value": "SWITCH,LEVEL", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2004", "quality": "Confirmed"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "MAX PRESS: 103 BAR Max @ 40C, AMB TEMP: -40°C TO +70°C, L=400uH, I=94mA, OUTPUT: 8 OR 13mA, Pi=0.87W", "quality": "Verify"}, "hazardous_classification": {"value": "EEx II C T6/T5, CERT NO. 00ATEX008X (partially legible), REF 65/16 112", "quality": "Verify"}}, "remarks": "Plate is heavily scratched/corroded; manufacturer logo and name are illegible. Certificate number (00ATEX008X) and reference code (65/16 112) partially obscured - verify against documentation. Model number's final digits are worn and could not be fully confirmed. No size, part number, weight, country, or month of manufacture are printed or legible on this plate. No tag number is visible on the plate itself, so the register tag 72-LSL-102X could not be cross-checked against printed text.", "qc_comment": "Significant surface wear and glare obscure the manufacturer name, part of the model/serial strings, and certification details. Recommend physical re-inspection or reference to original documentation to confirm make, exact model suffix, and full ATEX certificate number.", "photo_status": "HARD"}	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "915-P22A-010/9D1-1221-02", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "569789-01-001", "quality": "Verify"}, "tag_number": {"value": "72-LSL-102X", "quality": "Confirmed"}, "description": {"value": "SWITCH,LEVEL", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2004", "quality": "Confirmed"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "MAX PRESS: 103 BAR Max @ 40C, AMB TEMP: -40°C TO +70°C, L=400uH, I=94mA, OUTPUT: 8 OR 13mA, Pi=0.87W", "quality": "Verify"}, "hazardous_classification": {"value": "EEx II C T6/T5, CERT NO. 00ATEX008X (partially legible), REF 65/16 112", "quality": "Verify"}}, "remarks": "Plate is heavily scratched/corroded; manufacturer logo and name are illegible. Certificate number (00ATEX008X) and reference code (65/16 112) partially obscured - verify against documentation. Model number's final digits are worn and could not be fully confirmed. No size, part number, weight, country, or month of manufacture are printed or legible on this plate. No tag number is visible on the plate itself, so the register tag 72-LSL-102X could not be cross-checked against printed text.", "qc_comment": "Significant surface wear and glare obscure the manufacturer name, part of the model/serial strings, and certification details. Recommend physical re-inspection or reference to original documentation to confirm make, exact model suffix, and full ATEX certificate number.", "photo_status": "HARD"}	/data/storage/exports/72-LSL-102X/AI Output-72-LSL-102X-SWITCH,LEVEL.xlsx	/data/storage/exports/72-LSL-102X/72-LSL-102X-SWITCH,LEVEL-Template.xlsx	\N	3	1	2026-08-20 11:42:32.484037+00	2026-08-20 11:42:32.484037+00
47	12-M2-PIT-0008	ELECTRONIC PRESSURE TRANSMITTER	{"fields": {"make": {"value": "ROSEMOUNT", "quality": "Confirmed"}, "model": {"value": "3051TG4F2B81BS5BEK8Y2M5Q4Q8Q76T1P1Q15", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "UAE (Emerson FZE, Dubai)", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "24DUPG5030955", "quality": "Confirmed"}, "tag_number": {"value": "12-M2-PIT-0008", "quality": "Confirmed"}, "description": {"value": "ELECTRONIC PRESSURE TRANSMITTER", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2025", "quality": "Verify"}, "month_of_manufacture": {"value": "01", "quality": "Verify"}, "additional_information": {"value": "TYPE: 111, SW: 1.0.1, HW: 1.0.1, MAX W.P.: 4000PSI/276BAR, CAL: 0 TO 110 BAR G, SUPPLY (HART 4-20mA): 10.5-30V, SUPPLY (FOUNDATION Fieldbus/PROFIBUS-PA): 9-30V 17.5mA, INTEGRAL MANIFOLD MODEL: 0306RT22BA11SG, DATE CODE: 01/25, MARKINGS: CE, EAC, CSA(c/us)", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Model number is split across two label sections (front and side view) and partially obscured by rust/debris/insulation on the right side of the transmitter housing (photo 3, second image) — full model string reconstructed from both views, verify last characters. Date code '01/25' interpreted as month 01 / year 2025 per rule 5. No explicit ATEX/IECEx hazardous area marking visible on the Rosemount plate itself (only CE, EAC, CSA logos present) — verify if a separate Ex certification plate exists elsewhere on the unit. Country of origin inferred from 'Emerson FZE, Dubai, UAE' address line, not an explicit 'Country' field. Photos 1 (Weidmüller Klippon POK 91 Ex terminal, KEMA 03ATEX2077, tag not matching) and 2 (KJS Kookjae Korea valve tag plate, ANSI B16.34) appear to be different equipment nameplates unrelated to tag 12-M2-PIT-0008 and were not used for data extraction — flag for review to confirm they belong to this asset record or were misfiled.", "qc_comment": "Primary data sourced from the Rosemount transmitter plate (photo 3) which matches the register tag 12-M2-PIT-0008. Weidmüller and KJS valve nameplates (photos 1 & 2) do not correspond to this tag and were excluded from field extraction but noted in remarks for verification. Long alphanumeric model code should be double-checked against purchase order/datasheet due to glare and partial obstruction.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "ROSEMOUNT", "quality": "Confirmed"}, "model": {"value": "3051TG4F2B81BS5BEK8Y2M5Q4Q8Q76T1P1Q15", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "UAE (Emerson FZE, Dubai)", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "24DUPG5030955", "quality": "Confirmed"}, "tag_number": {"value": "12-M2-PIT-0008", "quality": "Confirmed"}, "description": {"value": "ELECTRONIC PRESSURE TRANSMITTER", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2025", "quality": "Verify"}, "month_of_manufacture": {"value": "01", "quality": "Verify"}, "additional_information": {"value": "TYPE: 111, SW: 1.0.1, HW: 1.0.1, MAX W.P.: 4000PSI/276BAR, CAL: 0 TO 110 BAR G, SUPPLY (HART 4-20mA): 10.5-30V, SUPPLY (FOUNDATION Fieldbus/PROFIBUS-PA): 9-30V 17.5mA, INTEGRAL MANIFOLD MODEL: 0306RT22BA11SG, DATE CODE: 01/25, MARKINGS: CE, EAC, CSA(c/us)", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Model number is split across two label sections (front and side view) and partially obscured by rust/debris/insulation on the right side of the transmitter housing (photo 3, second image) — full model string reconstructed from both views, verify last characters. Date code '01/25' interpreted as month 01 / year 2025 per rule 5. No explicit ATEX/IECEx hazardous area marking visible on the Rosemount plate itself (only CE, EAC, CSA logos present) — verify if a separate Ex certification plate exists elsewhere on the unit. Country of origin inferred from 'Emerson FZE, Dubai, UAE' address line, not an explicit 'Country' field. Photos 1 (Weidmüller Klippon POK 91 Ex terminal, KEMA 03ATEX2077, tag not matching) and 2 (KJS Kookjae Korea valve tag plate, ANSI B16.34) appear to be different equipment nameplates unrelated to tag 12-M2-PIT-0008 and were not used for data extraction — flag for review to confirm they belong to this asset record or were misfiled.", "qc_comment": "Primary data sourced from the Rosemount transmitter plate (photo 3) which matches the register tag 12-M2-PIT-0008. Weidmüller and KJS valve nameplates (photos 1 & 2) do not correspond to this tag and were excluded from field extraction but noted in remarks for verification. Long alphanumeric model code should be double-checked against purchase order/datasheet due to glare and partial obstruction.", "photo_status": "MEDIUM"}	/data/storage/exports/12-M2-PIT-0008/AI Output-12-M2-PIT-0008-ELECTRONIC PRESSURE TRANSMITTER.xlsx	/data/storage/exports/12-M2-PIT-0008/12-M2-PIT-0008-ELECTRONIC PRESSURE TRANSMITTER-Template.xlsx	\N	2	1	2026-08-19 07:21:22.055696+00	2026-08-19 07:21:22.055696+00
61	12-4020-BV-0111	BALL VALVE	{"fields": {"make": {"value": "JC", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "21736-80-63", "quality": "Confirmed"}, "tag_number": {"value": "12-4020-BV-0111", "quality": "Confirmed"}, "description": {"value": "BALL VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\"X3/4\\"", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Verify"}, "month_of_manufacture": {"value": "02", "quality": "Verify"}, "additional_information": {"value": "CLASS: 1500#, BODY: LF2, SEAT: PEEK, STEM: F51, BALL: F316(L), DATE CODE: 02/24, PRESSURE RATING 1: 255.3 BAR, TEMP RATING 1: -50.38°C, PRESSURE RATING 2: 225.4 BAR, TEMP RATING 2: 150°C, STANDARD: ASME B16.10 (partially legible), DRAWING/REF CODE: AGDC LOE 05 AR 023 (partially legible)", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Tag number and description supplied from asset register, not visible on plate itself. Some fields (make, model, part no, weight, country, hazardous classification) not printed or not legible on nameplate. Date code '02/24' interpreted as month 02, year 2024 per convention. Standard code partially obscured, read as 'ASME B16.10' from photo 2; leftmost columns of tag partially cut off/blurred in both photos, could not confirm full manufacturer name beyond 'JC' logo.", "qc_comment": "Nameplate is metallic and reflective with glare in places; left edge of label is cropped/blurred in both photos, obscuring standard code and possibly a manufacturer name. Core technical data (size, class, body/seat/stem/ball materials, pressure/temp ratings, serial number, date code) are clearly legible and consistent across both photos.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "JC", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "21736-80-63", "quality": "Confirmed"}, "tag_number": {"value": "12-4020-BV-0111", "quality": "Confirmed"}, "description": {"value": "BALL VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\"X3/4\\"", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Verify"}, "month_of_manufacture": {"value": "02", "quality": "Verify"}, "additional_information": {"value": "CLASS: 1500#, BODY: LF2, SEAT: PEEK, STEM: F51, BALL: F316(L), DATE CODE: 02/24, PRESSURE RATING 1: 255.3 BAR, TEMP RATING 1: -50.38°C, PRESSURE RATING 2: 225.4 BAR, TEMP RATING 2: 150°C, STANDARD: ASME B16.10 (partially legible), DRAWING/REF CODE: AGDC LOE 05 AR 023 (partially legible)", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Tag number and description supplied from asset register, not visible on plate itself. Some fields (make, model, part no, weight, country, hazardous classification) not printed or not legible on nameplate. Date code '02/24' interpreted as month 02, year 2024 per convention. Standard code partially obscured, read as 'ASME B16.10' from photo 2; leftmost columns of tag partially cut off/blurred in both photos, could not confirm full manufacturer name beyond 'JC' logo.", "qc_comment": "Nameplate is metallic and reflective with glare in places; left edge of label is cropped/blurred in both photos, obscuring standard code and possibly a manufacturer name. Core technical data (size, class, body/seat/stem/ball materials, pressure/temp ratings, serial number, date code) are clearly legible and consistent across both photos.", "photo_status": "MEDIUM"}	/data/storage/exports/12-4020-BV-0111/AI Output-12-4020-BV-0111-BALL VALVE.xlsx	/data/storage/exports/12-4020-BV-0111/12-4020-BV-0111-BALL VALVE-Template.xlsx	\N	3	1	2026-08-19 11:47:14.283894+00	2026-08-19 11:47:14.283894+00
77	73-TV-208X	VALVE,CONTROL,TEMPERATURE,3IN	{"fields": {"make": {"value": "NIIGATA MASONEILAN CO., LTD", "quality": "Confirmed"}, "model": {"value": "88-90685", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "DC11A1934-1", "quality": "Verify"}, "tag_number": {"value": "73-TV-208X", "quality": "Confirmed"}, "description": {"value": "VALVE,CONTROL,TEMPERATURE,3IN", "quality": "Confirmed"}, "size_dimension": {"value": "3\\" BODY / 3\\" PORT", "quality": "Verify"}, "year_of_manufacture": {"value": "2005", "quality": "Verify"}, "month_of_manufacture": {"value": "03", "quality": "Verify"}, "additional_information": {"value": "RATING: ASME CLASS 300 RF, SIZE:BODY 3\\" CV 75, PORT: 3\\", MAT'L BODY: ASTM A216 GR WCB, PLUG: SCS14A STELL. SEAT, SEAT: SUS403, FAIL ACTION: BOTTOM CLOSE, RANGE: 0.75-2.4 BAR, SUPPLY: 3.5 BAR, TRAVEL: 38.1MM (1-1/2\\"), CHARACT: LINEAR, GREASE DATE: MAR.08.2005", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Plate tag reads 'TV-208X' (register tag '73-TV-208X' includes area prefix not shown on plate — no mismatch, just abbreviated). Model No. and Serial No. are partially worn/corroded and hard to confirm exactly. 'ASME' rating text partly obscured but inferred from context. Grease/Date field (MAR.08.2005) used as best available manufacture date reference — actual manufacture date not separately labeled. Country of origin not printed; manufacturer name suggests Japan but not confirmed on plate. Heavy corrosion and glare across upper-left portion of label reduce legibility.", "qc_comment": "Nameplate heavily corroded/worn at edges and partially glared; several fields (model, serial, size, rating) required interpretation from faint stamped characters. Recommend physical verification of model and serial numbers before finalizing asset register entry.", "photo_status": "HARD"}	{"fields": {"make": {"value": "NIIGATA MASONEILAN CO., LTD", "quality": "Confirmed"}, "model": {"value": "88-90685", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "DC11A1934-1", "quality": "Verify"}, "tag_number": {"value": "73-TV-208X", "quality": "Confirmed"}, "description": {"value": "VALVE,CONTROL,TEMPERATURE,3IN", "quality": "Confirmed"}, "size_dimension": {"value": "3\\" BODY / 3\\" PORT", "quality": "Verify"}, "year_of_manufacture": {"value": "2005", "quality": "Verify"}, "month_of_manufacture": {"value": "03", "quality": "Verify"}, "additional_information": {"value": "RATING: ASME CLASS 300 RF, SIZE:BODY 3\\" CV 75, PORT: 3\\", MAT'L BODY: ASTM A216 GR WCB, PLUG: SCS14A STELL. SEAT, SEAT: SUS403, FAIL ACTION: BOTTOM CLOSE, RANGE: 0.75-2.4 BAR, SUPPLY: 3.5 BAR, TRAVEL: 38.1MM (1-1/2\\"), CHARACT: LINEAR, GREASE DATE: MAR.08.2005", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Plate tag reads 'TV-208X' (register tag '73-TV-208X' includes area prefix not shown on plate — no mismatch, just abbreviated). Model No. and Serial No. are partially worn/corroded and hard to confirm exactly. 'ASME' rating text partly obscured but inferred from context. Grease/Date field (MAR.08.2005) used as best available manufacture date reference — actual manufacture date not separately labeled. Country of origin not printed; manufacturer name suggests Japan but not confirmed on plate. Heavy corrosion and glare across upper-left portion of label reduce legibility.", "qc_comment": "Nameplate heavily corroded/worn at edges and partially glared; several fields (model, serial, size, rating) required interpretation from faint stamped characters. Recommend physical verification of model and serial numbers before finalizing asset register entry.", "photo_status": "HARD"}	/data/storage/exports/73-TV-208X/AI Output-73-TV-208X-VALVE,CONTROL,TEMPERATURE,3IN.xlsx	/data/storage/exports/73-TV-208X/73-TV-208X-VALVE,CONTROL,TEMPERATURE,3IN-Template.xlsx	\N	3	1	2026-08-20 11:42:54.897116+00	2026-08-20 11:42:54.897116+00
41	21-JDD-01	JUNCTION BOX,INSTRUMENT	{"fields": {"make": {"value": "Weidmüller", "quality": "Confirmed"}, "model": {"value": "Klippon POK 91 Ex", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "GERMANY", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "XB-KR-A-000127", "quality": "Confirmed"}, "tag_number": {"value": "21-JDD-01", "quality": "Confirmed"}, "description": {"value": "JUNCTION BOX,INSTRUMENT", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2005", "quality": "Confirmed"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "MANUFACTURER ADDRESS: WEIDMÜLLER INTERFACE GmbH & Co. KG, KLINGENBERGSTR 16, 32758 DETMOLD, GERMANY, CERTIFICATION BODY: KEMA, NOTIFIED BODY NUMBER: 0344", "quality": "Confirmed"}, "hazardous_classification": {"value": "II 2G EEx e II T6, II 2(1)G EEx e(ia) IIC T6, II 1G EEx ia IIC T6, KEMA 03ATEX2077", "quality": "Confirmed"}}, "remarks": "Tag number and description taken from asset register per instructions; plate itself shows no tag number, so no mismatch to flag. Size/dimension, part number, weight, and month of manufacture are not printed on this nameplate.", "qc_comment": "Plate is clear and well-lit apart from minor rust spots; all printed text is legible.", "photo_status": "EASY"}	{"fields": {"make": {"value": "Weidmüller11", "quality": "Confirmed"}, "model": {"value": "Klippon POK 91 Ex", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "GERMANY", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "XB-KR-A-000127", "quality": "Confirmed"}, "tag_number": {"value": "21-JDD-01", "quality": "Confirmed"}, "description": {"value": "JUNCTION BOX,INSTRUMENT", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2005", "quality": "Confirmed"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "MANUFACTURER ADDRESS: WEIDMÜLLER INTERFACE GmbH & Co. KG, KLINGENBERGSTR 16, 32758 DETMOLD, GERMANY, CERTIFICATION BODY: KEMA, NOTIFIED BODY NUMBER: 0344", "quality": "Confirmed"}, "hazardous_classification": {"value": "II 2G EEx e II T6, II 2(1)G EEx e(ia) IIC T6, II 1G EEx ia IIC T6, KEMA 03ATEX2077", "quality": "Confirmed"}}, "remarks": "Tag number and description taken from asset register per instructions; plate itself shows no tag number, so no mismatch to flag. Size/dimension, part number, weight, and month of manufacture are not printed on this nameplate.", "qc_comment": "Plate is clear and well-lit apart from minor rust spots; all printed text is legible.", "photo_status": "EASY"}	/data/storage/exports/21-JDD-01/AI Output-21-JDD-01-JUNCTION BOX,INSTRUMENT.xlsx	/data/storage/exports/21-JDD-01/21-JDD-01-JUNCTION BOX,INSTRUMENT-Template.xlsx	3	2	2	2026-08-18 06:26:23.586777+00	2026-08-19 08:25:24.25938+00
62	16-GV-1982	VALVE,GATE	{"fields": {"make": {"value": "YDF", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "YDF2403659-10-10", "quality": "Confirmed"}, "tag_number": {"value": "16-GV-1982", "quality": "Confirmed"}, "description": {"value": "VALVE,GATE", "quality": "Confirmed"}, "size_dimension": {"value": "2\\"", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "06", "quality": "Confirmed"}, "additional_information": {"value": "TYPE: GATE, CLASS: 300, MOP/PSI@100°F: 750 PSI@100°F, BODY: F53, STEM: F53, DISC: F53/STL, SEAT: F53/STL, FIG: 8, STANDARD: API 602/API 603/API 6D (partially obscured), ASME B16.34", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Standard reference text near S.N. (API 60X/... ASME B16.34) is partially obscured by glare and stem, transcribed best-effort — verify. No country, weight, part number, or model explicitly printed on plate. Date printed as 2024.06 (year.month), interpreted as June 2024.", "qc_comment": "Core valve data (type, size, class, pressure/temp rating, body/stem/disc/seat materials, serial number, date) clearly legible. Standard/certification line near bottom is glare-affected and should be re-verified in person.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "YDF", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "YDF2403659-10-10", "quality": "Confirmed"}, "tag_number": {"value": "16-GV-1982", "quality": "Confirmed"}, "description": {"value": "VALVE,GATE", "quality": "Confirmed"}, "size_dimension": {"value": "2\\"", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "06", "quality": "Confirmed"}, "additional_information": {"value": "TYPE: GATE, CLASS: 300, MOP/PSI@100°F: 750 PSI@100°F, BODY: F53, STEM: F53, DISC: F53/STL, SEAT: F53/STL, FIG: 8, STANDARD: API 602/API 603/API 6D (partially obscured), ASME B16.34", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Standard reference text near S.N. (API 60X/... ASME B16.34) is partially obscured by glare and stem, transcribed best-effort — verify. No country, weight, part number, or model explicitly printed on plate. Date printed as 2024.06 (year.month), interpreted as June 2024.", "qc_comment": "Core valve data (type, size, class, pressure/temp rating, body/stem/disc/seat materials, serial number, date) clearly legible. Standard/certification line near bottom is glare-affected and should be re-verified in person.", "photo_status": "MEDIUM"}	/data/storage/exports/16-GV-1982/AI Output-16-GV-1982-VALVE,GATE.xlsx	/data/storage/exports/16-GV-1982/16-GV-1982-VALVE,GATE-Template.xlsx	\N	2	1	2026-08-19 12:04:39.778652+00	2026-08-19 12:04:39.778652+00
68	35-SFX-015	FIRE EXTINGUISHER,DCP,9KG	{"fields": {"make": {"value": "QATAR FACTORY FOR FIRE FIGHTING EQUIPMENT & SAFETY SYSTEMS", "quality": "Confirmed"}, "model": {"value": "NQPS9", "quality": "Confirmed"}, "weight": {"value": "9 KG", "quality": "Confirmed"}, "country": {"value": "QATAR", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "35-SFX-015", "quality": "Confirmed"}, "description": {"value": "FIRE EXTINGUISHER,DCP,9KG", "quality": "Confirmed"}, "size_dimension": {"value": "9 KG", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "EXTINGUISHING MEDIUM: BC POWDER, RATING: 233B C, APPROVAL/LIC. NO.: KM 712098, MAX OPERATING PRESSURE PS: 18.5 BAR, TEST PRESSURE PT: 30 BAR, PROPELLANT: NITROGEN+HELIUM, TEMPERATURE RANGE: -20°C TO +60°C, OPERATING PRESSURE: 15 BAR, MANUFACTURED TO COMPLY WITH BS EN3, ADDRESS: NEW INDUSTRIAL AREA, P.O. BOX 55644, DOHA QATAR, TEL: 00974 44025888, FAX: 00974 44114630, EMAIL: info@qatarfactory.qa", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Tag number and description supplied from asset register per instructions; not physically visible on the plate photographed (label shows model/spec details only). Serial number and part number are not printed on the nameplate. Month of manufacture not shown, only year 2025. Some text near right edge is torn/obscured (plastic wrap damage) - operating pressure value for 'NQPS9' line partially cut off, reconstructed from visible characters.", "qc_comment": "Label largely legible but plastic wrap glare and a torn section on the right edge obscure some values; recommend physical verification of serial/part number absence and confirm operating pressure figures.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "QATAR FACTORY FOR FIRE FIGHTING EQUIPMENT & SAFETY SYSTEMS", "quality": "Confirmed"}, "model": {"value": "NQPS9", "quality": "Confirmed"}, "weight": {"value": "9 KG", "quality": "Confirmed"}, "country": {"value": "QATAR", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "35-SFX-015", "quality": "Confirmed"}, "description": {"value": "FIRE EXTINGUISHER,DCP,9KG", "quality": "Confirmed"}, "size_dimension": {"value": "9 KG", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "EXTINGUISHING MEDIUM: BC POWDER, RATING: 233B C, APPROVAL/LIC. NO.: KM 712098, MAX OPERATING PRESSURE PS: 18.5 BAR, TEST PRESSURE PT: 30 BAR, PROPELLANT: NITROGEN+HELIUM, TEMPERATURE RANGE: -20°C TO +60°C, OPERATING PRESSURE: 15 BAR, MANUFACTURED TO COMPLY WITH BS EN3, ADDRESS: NEW INDUSTRIAL AREA, P.O. BOX 55644, DOHA QATAR, TEL: 00974 44025888, FAX: 00974 44114630, EMAIL: info@qatarfactory.qa", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Tag number and description supplied from asset register per instructions; not physically visible on the plate photographed (label shows model/spec details only). Serial number and part number are not printed on the nameplate. Month of manufacture not shown, only year 2025. Some text near right edge is torn/obscured (plastic wrap damage) - operating pressure value for 'NQPS9' line partially cut off, reconstructed from visible characters.", "qc_comment": "Label largely legible but plastic wrap glare and a torn section on the right edge obscure some values; recommend physical verification of serial/part number absence and confirm operating pressure figures.", "photo_status": "MEDIUM"}	/data/storage/exports/35-SFX-015/AI Output-35-SFX-015-FIRE EXTINGUISHER,DCP,9KG.xlsx	/data/storage/exports/35-SFX-015/35-SFX-015-FIRE EXTINGUISHER,DCP,9KG-Template.xlsx	\N	3	1	2026-08-20 11:26:05.313752+00	2026-08-20 11:26:05.313752+00
48	12-4020-BV	0073,BALL VALVE	{"fields": {"make": {"value": "JC", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "22224-70-273 (Photo 1) / 21736-80-96 (Photo 2)", "quality": "Verify"}, "tag_number": {"value": "12-4020-BV", "quality": "Confirmed"}, "description": {"value": "0073,BALL VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\" X 3/4\\" 1500#", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Verify"}, "month_of_manufacture": {"value": "10 (Photo 1) / 02 (Photo 2)", "quality": "Verify"}, "additional_information": {"value": "STANDARDS: API 607, B16.10, ISO 17292; BODY: LF2; SEAT: PEEK; STEM: F316(L) (Photo 1) / F51 (Photo 2, partly obscured); BALL: F316(L); PRESSURE/TEMP RATING: 255.3 bar @ -50/38°C, 238.6 bar @ 84°C (Photo 1) vs 255.3 bar @ -50/38°C, 225.4 bar @ 150°C (Photo 2); MANUFACTURER MARK: 'JC' logo present on both plates", "quality": "Verify"}, "hazardous_classification": {"value": "Ex II 2GDc, LCIE 05 AR 023", "quality": "Verify"}}, "remarks": "Two photos appear to show two different nameplates (different serial numbers 22224-70-273 vs 21736-80-96, different date codes 10/24 vs 02/24, and differing pressure/temperature ratings and stem material). This may indicate a double-block-and-bleed valve assembly with two plates under one tag, or two separate valves photographed together. Recommend field verification to confirm which serial/date belongs to asset 12-4020-BV. Hazardous area marking partially obscured by glare/wire tag in Photo 2; 'Ex II 2GDc' reading uncertain. No manufacturer name, model, part number, weight, or country of origin printed on either plate; 'JC' logo assumed to represent maker's mark only.", "qc_comment": "Conflicting serial numbers, dates, and pressure/temperature data between the two photos suggest two distinct nameplates rather than duplicate views of one plate — verify on-site which corresponds to tag 12-4020-BV before finalizing register entry.", "photo_status": "HARD"}	{"fields": {"make": {"value": "JC", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "22224-70-273 (Photo 1) / 21736-80-96 (Photo 2)", "quality": "Verify"}, "tag_number": {"value": "12-4020-BV", "quality": "Confirmed"}, "description": {"value": "0073,BALL VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\" X 3/4\\" 1500#", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Verify"}, "month_of_manufacture": {"value": "10 (Photo 1) / 02 (Photo 2)", "quality": "Verify"}, "additional_information": {"value": "STANDARDS: API 607, B16.10, ISO 17292; BODY: LF2; SEAT: PEEK; STEM: F316(L) (Photo 1) / F51 (Photo 2, partly obscured); BALL: F316(L); PRESSURE/TEMP RATING: 255.3 bar @ -50/38°C, 238.6 bar @ 84°C (Photo 1) vs 255.3 bar @ -50/38°C, 225.4 bar @ 150°C (Photo 2); MANUFACTURER MARK: 'JC' logo present on both plates", "quality": "Verify"}, "hazardous_classification": {"value": "Ex II 2GDc, LCIE 05 AR 023", "quality": "Verify"}}, "remarks": "Two photos appear to show two different nameplates (different serial numbers 22224-70-273 vs 21736-80-96, different date codes 10/24 vs 02/24, and differing pressure/temperature ratings and stem material). This may indicate a double-block-and-bleed valve assembly with two plates under one tag, or two separate valves photographed together. Recommend field verification to confirm which serial/date belongs to asset 12-4020-BV. Hazardous area marking partially obscured by glare/wire tag in Photo 2; 'Ex II 2GDc' reading uncertain. No manufacturer name, model, part number, weight, or country of origin printed on either plate; 'JC' logo assumed to represent maker's mark only.", "qc_comment": "Conflicting serial numbers, dates, and pressure/temperature data between the two photos suggest two distinct nameplates rather than duplicate views of one plate — verify on-site which corresponds to tag 12-4020-BV before finalizing register entry.", "photo_status": "HARD"}	/data/storage/exports/12-4020-BV/AI Output-12-4020-BV-0073,BALL VALVE.xlsx	/data/storage/exports/12-4020-BV/12-4020-BV-0073,BALL VALVE-Template.xlsx	\N	3	1	2026-08-19 09:23:49.464594+00	2026-08-19 09:23:49.464594+00
49	12-4020-FDI-21-0003	INFRARED FLAME DETECTOR	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "FL4000H-5-0-1-3-1-1-1", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "BRAZIL", "quality": "Verify"}, "part_no": {"value": "P/N: 71296-1", "quality": "Verify"}, "serial_no": {"value": "23G3FX1G34X", "quality": "Verify"}, "tag_number": {"value": "12-4020-FDI-21-0003", "quality": "Confirmed"}, "description": {"value": "INFRARED FLAME DETECTOR", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2022", "quality": "Verify"}, "month_of_manufacture": {"value": "05", "quality": "Verify"}, "additional_information": {"value": "STANDARD: EN 54-10, SENSITIVITY: CLASS 1 AT HIGH & MEDIUM SENSITIVITY / CLASS 2 AT LOW SENSITIVITY, FIRMWARE: REV P, RELAY RATINGS: SEE MANUAL, BARCODE: 02883454, CERTIFICATION: INMETRO / SEGURANÇA, WARNING: POTENTIAL ELECTROSTATIC CHARGING HAZARD - USE ONLY DAMP CLOTH FOR CLEANING, WARNING: KEEP COVER TIGHT WHEN CIRCUITS ARE LIVE", "quality": "Verify"}, "hazardous_classification": {"value": "EX IB IIC T5 GB, EX TB IIIC T100°C DB, NCC 22.0087X, IP66/67, -40°C TO +80°C", "quality": "Verify"}}, "remarks": "Plate is photographed at an angle with some text upside-down and partially glared, making the serial number, part number, and date code difficult to fully confirm. Manufacturer name is not explicitly printed; only certification marks (INMETRO, Segurança) are visible. Date code 'Q/05-22' interpreted as month 05, year 2022 per instructions, but this could also represent a quarter code rather than a month - verify. Country inferred from Brazilian INMETRO/NCC certification, not explicitly stated as country of manufacture. Tag number and description taken from asset register as instructed; a similar tag string appears etched on the mounting bracket but is upside-down and not fully legible for cross-verification.", "qc_comment": "Recommend a follow-up photo taken square-on to the nameplate with better lighting to confirm serial number, part number suffix, and exact date code (month vs quarter) before finalizing asset register entry.", "photo_status": "HARD"}	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "FL4000H-5-0-1-3-1-1-1", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "BRAZIL", "quality": "Verify"}, "part_no": {"value": "P/N: 71296-1", "quality": "Verify"}, "serial_no": {"value": "23G3FX1G34X", "quality": "Verify"}, "tag_number": {"value": "12-4020-FDI-21-0003", "quality": "Confirmed"}, "description": {"value": "INFRARED FLAME DETECTOR", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2022", "quality": "Verify"}, "month_of_manufacture": {"value": "05", "quality": "Verify"}, "additional_information": {"value": "STANDARD: EN 54-10, SENSITIVITY: CLASS 1 AT HIGH & MEDIUM SENSITIVITY / CLASS 2 AT LOW SENSITIVITY, FIRMWARE: REV P, RELAY RATINGS: SEE MANUAL, BARCODE: 02883454, CERTIFICATION: INMETRO / SEGURANÇA, WARNING: POTENTIAL ELECTROSTATIC CHARGING HAZARD - USE ONLY DAMP CLOTH FOR CLEANING, WARNING: KEEP COVER TIGHT WHEN CIRCUITS ARE LIVE", "quality": "Verify"}, "hazardous_classification": {"value": "EX IB IIC T5 GB, EX TB IIIC T100°C DB, NCC 22.0087X, IP66/67, -40°C TO +80°C", "quality": "Verify"}}, "remarks": "Plate is photographed at an angle with some text upside-down and partially glared, making the serial number, part number, and date code difficult to fully confirm. Manufacturer name is not explicitly printed; only certification marks (INMETRO, Segurança) are visible. Date code 'Q/05-22' interpreted as month 05, year 2022 per instructions, but this could also represent a quarter code rather than a month - verify. Country inferred from Brazilian INMETRO/NCC certification, not explicitly stated as country of manufacture. Tag number and description taken from asset register as instructed; a similar tag string appears etched on the mounting bracket but is upside-down and not fully legible for cross-verification.", "qc_comment": "Recommend a follow-up photo taken square-on to the nameplate with better lighting to confirm serial number, part number suffix, and exact date code (month vs quarter) before finalizing asset register entry.", "photo_status": "HARD"}	/data/storage/exports/12-4020-FDI-21-0003/AI Output-12-4020-FDI-21-0003-INFRARED FLAME DETECTOR.xlsx	/data/storage/exports/12-4020-FDI-21-0003/12-4020-FDI-21-0003-INFRARED FLAME DETECTOR-Template.xlsx	\N	3	1	2026-08-19 09:36:11.163132+00	2026-08-19 09:36:11.163132+00
63	PM	8981B MOTOR,PUMP	{"fields": {"make": {"value": "ABB", "quality": "Confirmed"}, "model": {"value": "M3GP 71MD 4 IMB5/IM3001", "quality": "Confirmed"}, "weight": {"value": "10 kg", "quality": "Verify"}, "country": {"value": "FINLAND", "quality": "Confirmed"}, "part_no": {"value": "2413790-B", "quality": "Verify"}, "serial_no": {"value": "3G1F2405961912", "quality": "Confirmed"}, "tag_number": {"value": "PM", "quality": "Confirmed"}, "description": {"value": "8981B MOTOR,PUMP", "quality": "Confirmed"}, "size_dimension": {"value": "M3GP 71MD 4", "quality": "Verify"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "STANDARD: IEC60034-1, AMBIENT: -20C...+52C, VOLTAGE: 415V D, FREQUENCY: 50Hz, POWER: 0.18kW, SPEED: 1447 r/min, CURRENT: 0.5A, COS_PHI: 0.65, INSULATION_CLASS: F, IP_RATING: IP55, DUTY: S1, PRODUCT_CODE: 3GGP072340-BDL +VC, CERT_REF: 6202-27/C3, MANUFACTURER_ADDRESS: ABB Oy, IEC LV Motors, Stromberginpuistotie 5A, 65320 Vaasa, Finland", "quality": "Verify"}, "hazardous_classification": {"value": "EX EC II C T3 GC, EX II 3G, ATEX 2076X, IECEX UL 18.0081X", "quality": "Verify"}}, "remarks": "Nameplate photographed at an angle with some glare across the middle rows of the rating table (voltage/current columns largely blank/illegible beyond the printed 415V/50Hz/0.18kW/1447rpm/0.5A/0.65 values). Weight '10 kg' is partially cut off at bottom edge of plate and should be verified. Part number field is inferred from the code '2413790-B' printed near top left, which may be a design/type reference rather than a discrete part number. Month of manufacture is not explicitly printed; only '2024' year is shown. No tag number is printed on the plate itself, so no mismatch could be checked against the register tag 'PM'.", "qc_comment": "Core electrical and identification data (make, model, serial, voltage, power, speed) are clearly legible; verify weight, part number, and hazardous classification certificate numbers due to glare and small/worn text in those areas.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "ABB", "quality": "Confirmed"}, "model": {"value": "M3GP 71MD 4 IMB5/IM3001", "quality": "Confirmed"}, "weight": {"value": "10 kg", "quality": "Verify"}, "country": {"value": "FINLAND", "quality": "Confirmed"}, "part_no": {"value": "2413790-B", "quality": "Verify"}, "serial_no": {"value": "3G1F2405961912", "quality": "Confirmed"}, "tag_number": {"value": "PM", "quality": "Confirmed"}, "description": {"value": "8981B MOTOR,PUMP", "quality": "Confirmed"}, "size_dimension": {"value": "M3GP 71MD 4", "quality": "Verify"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "STANDARD: IEC60034-1, AMBIENT: -20C...+52C, VOLTAGE: 415V D, FREQUENCY: 50Hz, POWER: 0.18kW, SPEED: 1447 r/min, CURRENT: 0.5A, COS_PHI: 0.65, INSULATION_CLASS: F, IP_RATING: IP55, DUTY: S1, PRODUCT_CODE: 3GGP072340-BDL +VC, CERT_REF: 6202-27/C3, MANUFACTURER_ADDRESS: ABB Oy, IEC LV Motors, Stromberginpuistotie 5A, 65320 Vaasa, Finland", "quality": "Verify"}, "hazardous_classification": {"value": "EX EC II C T3 GC, EX II 3G, ATEX 2076X, IECEX UL 18.0081X", "quality": "Verify"}}, "remarks": "Nameplate photographed at an angle with some glare across the middle rows of the rating table (voltage/current columns largely blank/illegible beyond the printed 415V/50Hz/0.18kW/1447rpm/0.5A/0.65 values). Weight '10 kg' is partially cut off at bottom edge of plate and should be verified. Part number field is inferred from the code '2413790-B' printed near top left, which may be a design/type reference rather than a discrete part number. Month of manufacture is not explicitly printed; only '2024' year is shown. No tag number is printed on the plate itself, so no mismatch could be checked against the register tag 'PM'.", "qc_comment": "Core electrical and identification data (make, model, serial, voltage, power, speed) are clearly legible; verify weight, part number, and hazardous classification certificate numbers due to glare and small/worn text in those areas.", "photo_status": "MEDIUM"}	/data/storage/exports/PM/AI Output-PM-8981B MOTOR,PUMP.xlsx	/data/storage/exports/PM/PM-8981B MOTOR,PUMP-Template.xlsx	\N	2	1	2026-08-19 12:05:08.597256+00	2026-08-19 12:05:08.597256+00
69	35-XL-01A-018	BEACON,FLASH,AMBER,24VDC	{"fields": {"make": {"value": "e2S", "quality": "Confirmed"}, "model": {"value": "D1xB2X05DC024", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "UK", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "24/01DB12/05863", "quality": "Confirmed"}, "tag_number": {"value": "35-XL-01A-018", "quality": "Confirmed"}, "description": {"value": "BEACON,FLASH,AMBER,24VDC", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2024", "quality": "Verify"}, "month_of_manufacture": {"value": "01", "quality": "Verify"}, "additional_information": {"value": "PRODUCT: D1xB2 Xenon Beacon, NOMINAL VOLTAGE: 24V dc, VOLTAGE RANGE: 20-28V dc, NOMINAL CURRENT: 285mA, INSTRUCTION SHEET: D191-00-201-18, CABLE ENTRIES: 2-off M20 x1.5mm / 3-off 3/4\\" NPT, UL CERTIFIED: SAFETY USA E245313, MANUFACTURER ADDRESS: Impress House, Mansell Rd, London UK W3 7QH, www.e2s.com, COUNTRY OF ORIGIN: British Made / 英国制造, CCC MARK: present (no number legible), CHINESE LABEL: D1xB2X05DC024 信标 光源:氙光, WARNING (EN/FR bilingual): Do not open when explosive atmosphere present, do not open when energised, high voltage shock hazard - wait 5 minutes, do not paint, sealing fitting requirements per hazardous area installation standards", "quality": "Verify"}, "hazardous_classification": {"value": "ATEX/IECEx: II 2G Ex db IIC T4 Gb Ta -55°C to +80°C, Ex db IIC T5 Gb Ta -55°C to +75°C, Ex db IIC T6 Gb Ta -55°C to +60°C; II 2D Ex tb IIIC T104°C Db Ta -55°C to +80°C; NEC/CEC Class/Div: Class I Div1 Group ABCD T5 Ta -55°C to +80°C, Class II Div1 Group EFG T6 Ta -55°C to +80°C, Class III Div1 Ta -55°C to +80°C; NEC Class Zone: Class I Zone1 AEx db IIC T4 Ta -55°C to +80°C, Class I Zone1 AEx db IIC T5 Ta -55°C to +80°C, Zone21 AEx tb IIIC T89°C Ta -55°C to +80°C; CEC Class Zone: Ex db IIC T4 Ta -55°C to +80°C, Ex db IIC T5 Ta -55°C to +75°C, Ex db IIC T6 Ta -55°C to +80°C, Ex tb IIIC T89°C Ta -55°C to +80°C; DEMKO 19 ATEX 2006X; IECEx ULD 16.0008X; UL21UKEX3130X; UKCA 0518; CE 2813; EAC: EA3C RU C-GB.AA71.B.00273/20 - 1Ex d IIC T6 Gb X Ta -55°C to +60°C, 1Ex d IIC T5 Gb X Ta -55°C to +75°C, 1Ex d IIC T4 Gb X Ta -55°C to +80°C, Ex tb IIIC T104°C Db X Ta -55°C to +80°C; IP66, Type 4X/3R/13", "quality": "Confirmed"}}, "remarks": "Tag number and description taken from asset register as instructed; no tag number is printed on the nameplate itself for cross-check. Serial number '24/01DB12/05863' appears to encode a date prefix (24/01), interpreted as year 2024 / month 01 per instructions on date-code formats, but this is an inference from serial structure, not an explicit 'Date of Manufacture' field, so marked Verify. No explicit weight, size/dimension, or separate part number field found on any of the four plates. Multiple overlapping certification labels (ATEX/IECEx/UKCA/CE, EAC, UL, Chinese CCC) were cross-referenced across photos 1 and 4 for consistency.", "qc_comment": "Main technical nameplate (photo 1) and EAC label (photo 4) are sharp and consistent for model D1xB2X05DC024 and hazardous area ratings. Serial number and date inference should be verified against purchase/installation records. No weight, size, or discrete part number printed anywhere on the unit.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "e2S", "quality": "Confirmed"}, "model": {"value": "D1xB2X05DC024", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "UK", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "24/01DB12/05863", "quality": "Confirmed"}, "tag_number": {"value": "35-XL-01A-018", "quality": "Confirmed"}, "description": {"value": "BEACON,FLASH,AMBER,24VDC", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2024", "quality": "Verify"}, "month_of_manufacture": {"value": "01", "quality": "Verify"}, "additional_information": {"value": "PRODUCT: D1xB2 Xenon Beacon, NOMINAL VOLTAGE: 24V dc, VOLTAGE RANGE: 20-28V dc, NOMINAL CURRENT: 285mA, INSTRUCTION SHEET: D191-00-201-18, CABLE ENTRIES: 2-off M20 x1.5mm / 3-off 3/4\\" NPT, UL CERTIFIED: SAFETY USA E245313, MANUFACTURER ADDRESS: Impress House, Mansell Rd, London UK W3 7QH, www.e2s.com, COUNTRY OF ORIGIN: British Made / 英国制造, CCC MARK: present (no number legible), CHINESE LABEL: D1xB2X05DC024 信标 光源:氙光, WARNING (EN/FR bilingual): Do not open when explosive atmosphere present, do not open when energised, high voltage shock hazard - wait 5 minutes, do not paint, sealing fitting requirements per hazardous area installation standards", "quality": "Verify"}, "hazardous_classification": {"value": "ATEX/IECEx: II 2G Ex db IIC T4 Gb Ta -55°C to +80°C, Ex db IIC T5 Gb Ta -55°C to +75°C, Ex db IIC T6 Gb Ta -55°C to +60°C; II 2D Ex tb IIIC T104°C Db Ta -55°C to +80°C; NEC/CEC Class/Div: Class I Div1 Group ABCD T5 Ta -55°C to +80°C, Class II Div1 Group EFG T6 Ta -55°C to +80°C, Class III Div1 Ta -55°C to +80°C; NEC Class Zone: Class I Zone1 AEx db IIC T4 Ta -55°C to +80°C, Class I Zone1 AEx db IIC T5 Ta -55°C to +80°C, Zone21 AEx tb IIIC T89°C Ta -55°C to +80°C; CEC Class Zone: Ex db IIC T4 Ta -55°C to +80°C, Ex db IIC T5 Ta -55°C to +75°C, Ex db IIC T6 Ta -55°C to +80°C, Ex tb IIIC T89°C Ta -55°C to +80°C; DEMKO 19 ATEX 2006X; IECEx ULD 16.0008X; UL21UKEX3130X; UKCA 0518; CE 2813; EAC: EA3C RU C-GB.AA71.B.00273/20 - 1Ex d IIC T6 Gb X Ta -55°C to +60°C, 1Ex d IIC T5 Gb X Ta -55°C to +75°C, 1Ex d IIC T4 Gb X Ta -55°C to +80°C, Ex tb IIIC T104°C Db X Ta -55°C to +80°C; IP66, Type 4X/3R/13", "quality": "Confirmed"}}, "remarks": "Tag number and description taken from asset register as instructed; no tag number is printed on the nameplate itself for cross-check. Serial number '24/01DB12/05863' appears to encode a date prefix (24/01), interpreted as year 2024 / month 01 per instructions on date-code formats, but this is an inference from serial structure, not an explicit 'Date of Manufacture' field, so marked Verify. No explicit weight, size/dimension, or separate part number field found on any of the four plates. Multiple overlapping certification labels (ATEX/IECEx/UKCA/CE, EAC, UL, Chinese CCC) were cross-referenced across photos 1 and 4 for consistency.", "qc_comment": "Main technical nameplate (photo 1) and EAC label (photo 4) are sharp and consistent for model D1xB2X05DC024 and hazardous area ratings. Serial number and date inference should be verified against purchase/installation records. No weight, size, or discrete part number printed anywhere on the unit.", "photo_status": "MEDIUM"}	/data/storage/exports/35-XL-01A-018/AI Output-35-XL-01A-018-BEACON,FLASH,AMBER,24VDC.xlsx	/data/storage/exports/35-XL-01A-018/35-XL-01A-018-BEACON,FLASH,AMBER,24VDC-Template.xlsx	\N	3	1	2026-08-20 11:26:32.986278+00	2026-08-20 11:26:32.986278+00
50	12-4020-NLV-0007	NEEDLE VALVE	{"fields": {"make": {"value": "WIKA", "quality": "Confirmed"}, "model": {"value": "IV10-661615L", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "OPD 40-6911", "quality": "Verify"}, "serial_no": {"value": "HT 293629", "quality": "Verify"}, "tag_number": {"value": "12-4020-NLV-0007", "quality": "Confirmed"}, "description": {"value": "NEEDLE VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "IN-OUT 1/2\\" NPT-F, DRAIN 1/4\\" NPT-F", "quality": "Verify"}, "year_of_manufacture": {"value": "2025", "quality": "Verify"}, "month_of_manufacture": {"value": "03", "quality": "Verify"}, "additional_information": {"value": "MATERIAL: AISI 316/316L PTFE, PRESSURE_RATING: 420 bar / 6000 PSI @RT, TEMP_RANGE: -55°C / +210°C, DATE_CODE: CW11/25 (Calendar Week 11, 2025 - inferred month/year), FLOW_DIRECTION: arrow marked on body", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Plate is worn/stamped with low contrast, several digits (model number, part number, heat number) are partially obscured by surface texture and require verification against clearer reference or physical inspection. Date code 'CW11/25' interpreted as Calendar Week 11 of 2025, converted to approx. March 2025 for month/year fields - this is an inference, not a direct printed month. Tag number and description matched the register with no mismatch observed on plate (no distinct tag number visible on nameplate itself).", "qc_comment": "Two photos of the same WIKA needle valve nameplate; second photo (Photo 2) is sharper and was used to confirm most values. Recommend physical re-check of model code 'IV10-661615L', part number 'OPD 40-6911', and heat/lot number 'HT293629' due to stamping wear. No country of origin, weight, or hazardous area marking present on this plate.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "WIKA", "quality": "Confirmed"}, "model": {"value": "IV10-661615L", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "OPD 40-6911", "quality": "Verify"}, "serial_no": {"value": "HT 293629", "quality": "Verify"}, "tag_number": {"value": "12-4020-NLV-0007", "quality": "Confirmed"}, "description": {"value": "NEEDLE VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "IN-OUT 1/2\\" NPT-F, DRAIN 1/4\\" NPT-F", "quality": "Verify"}, "year_of_manufacture": {"value": "2025", "quality": "Verify"}, "month_of_manufacture": {"value": "03", "quality": "Verify"}, "additional_information": {"value": "MATERIAL: AISI 316/316L PTFE, PRESSURE_RATING: 420 bar / 6000 PSI @RT, TEMP_RANGE: -55°C / +210°C, DATE_CODE: CW11/25 (Calendar Week 11, 2025 - inferred month/year), FLOW_DIRECTION: arrow marked on body", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Plate is worn/stamped with low contrast, several digits (model number, part number, heat number) are partially obscured by surface texture and require verification against clearer reference or physical inspection. Date code 'CW11/25' interpreted as Calendar Week 11 of 2025, converted to approx. March 2025 for month/year fields - this is an inference, not a direct printed month. Tag number and description matched the register with no mismatch observed on plate (no distinct tag number visible on nameplate itself).", "qc_comment": "Two photos of the same WIKA needle valve nameplate; second photo (Photo 2) is sharper and was used to confirm most values. Recommend physical re-check of model code 'IV10-661615L', part number 'OPD 40-6911', and heat/lot number 'HT293629' due to stamping wear. No country of origin, weight, or hazardous area marking present on this plate.", "photo_status": "MEDIUM"}	/data/storage/exports/12-4020-NLV-0007/AI Output-12-4020-NLV-0007-NEEDLE VALVE.xlsx	/data/storage/exports/12-4020-NLV-0007/12-4020-NLV-0007-NEEDLE VALVE-Template.xlsx	\N	3	1	2026-08-19 09:36:34.540015+00	2026-08-19 09:36:34.540015+00
64	20-DZT-006	TRANSMITTER,DENSITY	{"fields": {"make": {"value": "MICRO MOTION INC", "quality": "Verify"}, "model": {"value": "FDM1XA721BBB2F00EZBX", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "USA", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "21542833", "quality": "Confirmed"}, "tag_number": {"value": "20-DZT-006", "quality": "Confirmed"}, "description": {"value": "TRANSMITTER,DENSITY", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "INPUT: SEE ATEX INSTRUCTIONS, PMAX: 50 BAR at 20°C, ETO51909, AE, MANUFACTURER: MICRO MOTION INC, BOULDER, CO, USA, EU IMPORTER: EMERSON PROCESS MANAGEMENT FLOW BV, EDE, NL, NOTE: *FOR AMBIENT TEMP RATING AND INPUT SEE ATEX INSTRUCTIONS - THIS UNIT INSTALLED IN HAZARDOUS LOCATIONS, PATENTED: www.patents.microflow.com", "quality": "Verify"}, "hazardous_classification": {"value": "II 1/2G Ex db IIC T* Ga/Gb, Sira 13ATEX2257 X, CE 2460", "quality": "Confirmed"}}, "remarks": "Tag number and description were provided from the asset register and copied unchanged; no tag number is visible on the plate itself for comparison. Part No. and month of manufacture are not legible/printed. Country inferred from manufacturer address (Boulder, CO, USA); EU importer address (Ede, NL) is also present but not the country of manufacture. Model and serial numbers are clear across both photos.", "qc_comment": "Two close-up photos of the same nameplate, partially obscured by fingers and a wire loop; core identification data (model, serial, ATEX marking) is legible and consistent between images.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "MICRO MOTION INC", "quality": "Verify"}, "model": {"value": "FDM1XA721BBB2F00EZBX", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "USA", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "21542833", "quality": "Confirmed"}, "tag_number": {"value": "20-DZT-006", "quality": "Confirmed"}, "description": {"value": "TRANSMITTER,DENSITY", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "INPUT: SEE ATEX INSTRUCTIONS, PMAX: 50 BAR at 20°C, ETO51909, AE, MANUFACTURER: MICRO MOTION INC, BOULDER, CO, USA, EU IMPORTER: EMERSON PROCESS MANAGEMENT FLOW BV, EDE, NL, NOTE: *FOR AMBIENT TEMP RATING AND INPUT SEE ATEX INSTRUCTIONS - THIS UNIT INSTALLED IN HAZARDOUS LOCATIONS, PATENTED: www.patents.microflow.com", "quality": "Verify"}, "hazardous_classification": {"value": "II 1/2G Ex db IIC T* Ga/Gb, Sira 13ATEX2257 X, CE 2460", "quality": "Confirmed"}}, "remarks": "Tag number and description were provided from the asset register and copied unchanged; no tag number is visible on the plate itself for comparison. Part No. and month of manufacture are not legible/printed. Country inferred from manufacturer address (Boulder, CO, USA); EU importer address (Ede, NL) is also present but not the country of manufacture. Model and serial numbers are clear across both photos.", "qc_comment": "Two close-up photos of the same nameplate, partially obscured by fingers and a wire loop; core identification data (model, serial, ATEX marking) is legible and consistent between images.", "photo_status": "MEDIUM"}	/data/storage/exports/20-DZT-006/AI Output-20-DZT-006-TRANSMITTER,DENSITY.xlsx	/data/storage/exports/20-DZT-006/20-DZT-006-TRANSMITTER,DENSITY-Template.xlsx	\N	2	1	2026-08-19 12:10:31.647575+00	2026-08-19 12:10:31.647575+00
70	16-NRV-1268	VALVE,CHECK,3INX300LBS	{"fields": {"make": {"value": "YDF", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "YDF2403660-10-13", "quality": "Confirmed"}, "tag_number": {"value": "16-NRV-1268", "quality": "Confirmed"}, "description": {"value": "VALVE,CHECK,3INX300LBS", "quality": "Confirmed"}, "size_dimension": {"value": "3\\" CLASS 300", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "07", "quality": "Confirmed"}, "additional_information": {"value": "STANDARD: API594/ASME B16.34, TYPE: CHECK VALVE, BODY: 6A, DISC: 6A+STL.6, PN: F53, SEAT: INT+STL.6, PRESSURE: 750 PSI @100°F, TEMP RANGE: -20°F~400°F", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate confirms tag details match register (no separate tag number printed on plate itself, only manufacturer serial/date data). A finger is partially obscuring the lower-right portion of the plate near the DATE and S/N fields; date code read as 07/2024 (month/year) based on visible digits. Some digits in the DATE field are slightly blurred and should be double-checked. No country of origin, weight, part number, or hazardous area marking is printed on this plate.", "qc_comment": "Core valve data (size, class, body/disc/seat materials, pressure/temp rating, serial and date) are legible and consistent with a YDF check valve nameplate. Fields with no printed value (weight, country, hazardous classification, part no., model) were marked as absent rather than guessed. Recommend a follow-up photo without finger obstruction to fully verify the S/N and DATE codes.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "YDF", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "YDF2403660-10-13", "quality": "Confirmed"}, "tag_number": {"value": "16-NRV-1268", "quality": "Confirmed"}, "description": {"value": "VALVE,CHECK,3INX300LBS", "quality": "Confirmed"}, "size_dimension": {"value": "3\\" CLASS 300", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "07", "quality": "Confirmed"}, "additional_information": {"value": "STANDARD: API594/ASME B16.34, TYPE: CHECK VALVE, BODY: 6A, DISC: 6A+STL.6, PN: F53, SEAT: INT+STL.6, PRESSURE: 750 PSI @100°F, TEMP RANGE: -20°F~400°F", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate confirms tag details match register (no separate tag number printed on plate itself, only manufacturer serial/date data). A finger is partially obscuring the lower-right portion of the plate near the DATE and S/N fields; date code read as 07/2024 (month/year) based on visible digits. Some digits in the DATE field are slightly blurred and should be double-checked. No country of origin, weight, part number, or hazardous area marking is printed on this plate.", "qc_comment": "Core valve data (size, class, body/disc/seat materials, pressure/temp rating, serial and date) are legible and consistent with a YDF check valve nameplate. Fields with no printed value (weight, country, hazardous classification, part no., model) were marked as absent rather than guessed. Recommend a follow-up photo without finger obstruction to fully verify the S/N and DATE codes.", "photo_status": "MEDIUM"}	/data/storage/exports/16-NRV-1268/AI Output-16-NRV-1268-VALVE,CHECK,3INX300LBS.xlsx	/data/storage/exports/16-NRV-1268/16-NRV-1268-VALVE,CHECK,3INX300LBS-Template.xlsx	\N	3	1	2026-08-20 11:27:45.354817+00	2026-08-20 11:27:45.354817+00
72	72-PSV-003B	VALVE,PRESSURE SAFETY,3-X 4IN,SP29.5BAR	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "CC-DA-RF-GS", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "TPQ904E-N", "quality": "Verify"}, "tag_number": {"value": "72-PSV-003B", "quality": "Confirmed"}, "description": {"value": "VALVE,PRESSURE SAFETY,3-X 4IN,SP29.5BAR", "quality": "Confirmed"}, "size_dimension": {"value": "3 X 4IN", "quality": "Verify"}, "year_of_manufacture": {"value": "2005", "quality": "Verify"}, "month_of_manufacture": {"value": "05", "quality": "Verify"}, "additional_information": {"value": "MEDIUM: AIR, SET PRESSURE: 4.6 BARG (approx), TEMP RATING: 7 DEG C (partially legible), CODE/REF: AGR 01, DATE CODE: 5/05 (interpreted as month 05, year 2005)", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate heavily worn/corroded; several characters on the top plate (model/serial/pressure lines) are only partially legible and best-effort transcriptions are flagged as Verify. Lower strip shows 'TAG 72-PSV-00...' consistent with register tag 72-PSV-003B, but the final digit/letter is obscured by rust and a bolt, so exact match cannot be fully confirmed from the image alone. No manufacturer name, country, weight, part number, or hazardous area marking are visible on the plate.", "qc_comment": "Plate is corroded and glare-affected; recommend physical re-inspection or higher-resolution image to confirm model/serial numbers, set pressure value, and full tag number before finalizing asset register entry.", "photo_status": "HARD"}	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "CC-DA-RF-GS", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "TPQ904E-N", "quality": "Verify"}, "tag_number": {"value": "72-PSV-003B", "quality": "Confirmed"}, "description": {"value": "VALVE,PRESSURE SAFETY,3-X 4IN,SP29.5BAR", "quality": "Confirmed"}, "size_dimension": {"value": "3 X 4IN", "quality": "Verify"}, "year_of_manufacture": {"value": "2005", "quality": "Verify"}, "month_of_manufacture": {"value": "05", "quality": "Verify"}, "additional_information": {"value": "MEDIUM: AIR, SET PRESSURE: 4.6 BARG (approx), TEMP RATING: 7 DEG C (partially legible), CODE/REF: AGR 01, DATE CODE: 5/05 (interpreted as month 05, year 2005)", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate heavily worn/corroded; several characters on the top plate (model/serial/pressure lines) are only partially legible and best-effort transcriptions are flagged as Verify. Lower strip shows 'TAG 72-PSV-00...' consistent with register tag 72-PSV-003B, but the final digit/letter is obscured by rust and a bolt, so exact match cannot be fully confirmed from the image alone. No manufacturer name, country, weight, part number, or hazardous area marking are visible on the plate.", "qc_comment": "Plate is corroded and glare-affected; recommend physical re-inspection or higher-resolution image to confirm model/serial numbers, set pressure value, and full tag number before finalizing asset register entry.", "photo_status": "HARD"}	/data/storage/exports/72-PSV-003B/AI Output-72-PSV-003B-VALVE,PRESSURE SAFETY,3-X 4IN,SP29.5BAR.xlsx	/data/storage/exports/72-PSV-003B/72-PSV-003B-VALVE,PRESSURE SAFETY,3-X 4IN,SP29.5BAR-Template.xlsx	\N	3	1	2026-08-20 11:29:46.815028+00	2026-08-20 11:29:46.815028+00
51	12-4020-BV-0073	BALL VALVE	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "22224-70-273", "quality": "Verify"}, "tag_number": {"value": "12-4020-BV-0073", "quality": "Confirmed"}, "description": {"value": "BALL VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\"X3/4\\" 1500#", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "10", "quality": "Confirmed"}, "additional_information": {"value": "STANDARDS: API 607, B16.10, ISO 17292, RGD LCIE 05 AR 023, BODY: LF2, SEAT: PEEK, STEM: F316(L), BALL: F316(L), PRESSURE/TEMP RATING: 255.3 bar at -50/38°C, 238.6 bar at 84°C, DATE CODE: 10/24", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Date code '10/24' interpreted as month 10, year 2024 per convention. Serial number partially obscured by glare at the end (last digit uncertain, read as '273'). Manufacturer name/logo not clearly visible on plate (small partial mark near right edge, illegible). Country, weight, part number, and hazardous area classification not printed on this plate.", "qc_comment": "Core valve specification data (size, materials, pressure/temp ratings, standards, date code) is clearly legible. Manufacturer identity, weight, and country of origin are absent or illegible on this plate; serial number end digit should be verified against a clearer image if available.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "Not present on nameplate", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "22224-70-273", "quality": "Verify"}, "tag_number": {"value": "12-4020-BV-0073", "quality": "Confirmed"}, "description": {"value": "BALL VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\"X3/4\\" 1500#", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "10", "quality": "Confirmed"}, "additional_information": {"value": "STANDARDS: API 607, B16.10, ISO 17292, RGD LCIE 05 AR 023, BODY: LF2, SEAT: PEEK, STEM: F316(L), BALL: F316(L), PRESSURE/TEMP RATING: 255.3 bar at -50/38°C, 238.6 bar at 84°C, DATE CODE: 10/24", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Date code '10/24' interpreted as month 10, year 2024 per convention. Serial number partially obscured by glare at the end (last digit uncertain, read as '273'). Manufacturer name/logo not clearly visible on plate (small partial mark near right edge, illegible). Country, weight, part number, and hazardous area classification not printed on this plate.", "qc_comment": "Core valve specification data (size, materials, pressure/temp ratings, standards, date code) is clearly legible. Manufacturer identity, weight, and country of origin are absent or illegible on this plate; serial number end digit should be verified against a clearer image if available.", "photo_status": "MEDIUM"}	/data/storage/exports/12-4020-BV-0073/AI Output-12-4020-BV-0073-BALL VALVE.xlsx	/data/storage/exports/12-4020-BV-0073/12-4020-BV-0073-BALL VALVE-Template.xlsx	\N	3	1	2026-08-19 09:42:35.554396+00	2026-08-19 09:42:35.554396+00
52	12-4020-BV-0083	BALL VALVE	{"fields": {"make": {"value": "JC", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "21736-80-96", "quality": "Confirmed"}, "tag_number": {"value": "12-4020-BV-0083", "quality": "Confirmed"}, "description": {"value": "BALL VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\"X3/4\\", 1500#", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Verify"}, "month_of_manufacture": {"value": "02", "quality": "Verify"}, "additional_information": {"value": "STANDARD: ISO 17292, STANDARD: B 16.10, STANDARD: API 607, BODY: LF2, SEAT: PEEK, STEM: F51, BALL: F316(L), PRESSURE RATING 1: 255.3 BAR AT -50/38°C, PRESSURE RATING 2: 225.4 BAR AT 150°C, DATE CODE: 02/24 (MONTH/YEAR)", "quality": "Confirmed"}, "hazardous_classification": {"value": "EX II 2GD C LCIE 05 AR 023", "quality": "Confirmed"}}, "remarks": "Date code '02/24' interpreted as month 02, year 2024 per convention; no explicit 'year of manufacture' label present, so value inferred from date code. Manufacturer identified only by 'JC' logo/mark on plate - no full company name legible. No model, part number, weight, or country of origin printed on nameplate. Tag number and description confirmed from asset register, matching plate context (no conflicting tag visible on plate itself).", "qc_comment": "Plate text is largely legible with good lighting, but small print (e.g., ISO/API codes, stem/ball material codes) required close inspection; a rusted metal tag partially obscures upper valve body but not the nameplate itself. Manufacturer identity should be verified against company records since only a logo/initials 'JC' appear.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "JC", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "21736-80-96", "quality": "Confirmed"}, "tag_number": {"value": "12-4020-BV-0083", "quality": "Confirmed"}, "description": {"value": "BALL VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\"X3/4\\", 1500#", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Verify"}, "month_of_manufacture": {"value": "02", "quality": "Verify"}, "additional_information": {"value": "STANDARD: ISO 17292, STANDARD: B 16.10, STANDARD: API 607, BODY: LF2, SEAT: PEEK, STEM: F51, BALL: F316(L), PRESSURE RATING 1: 255.3 BAR AT -50/38°C, PRESSURE RATING 2: 225.4 BAR AT 150°C, DATE CODE: 02/24 (MONTH/YEAR)", "quality": "Confirmed"}, "hazardous_classification": {"value": "EX II 2GD C LCIE 05 AR 023", "quality": "Confirmed"}}, "remarks": "Date code '02/24' interpreted as month 02, year 2024 per convention; no explicit 'year of manufacture' label present, so value inferred from date code. Manufacturer identified only by 'JC' logo/mark on plate - no full company name legible. No model, part number, weight, or country of origin printed on nameplate. Tag number and description confirmed from asset register, matching plate context (no conflicting tag visible on plate itself).", "qc_comment": "Plate text is largely legible with good lighting, but small print (e.g., ISO/API codes, stem/ball material codes) required close inspection; a rusted metal tag partially obscures upper valve body but not the nameplate itself. Manufacturer identity should be verified against company records since only a logo/initials 'JC' appear.", "photo_status": "MEDIUM"}	/data/storage/exports/12-4020-BV-0083/AI Output-12-4020-BV-0083-BALL VALVE.xlsx	/data/storage/exports/12-4020-BV-0083/12-4020-BV-0083-BALL VALVE-Template.xlsx	\N	3	1	2026-08-19 09:42:51.920968+00	2026-08-19 09:42:51.920968+00
71	35-GDF-01A-007	DETECTOR,FLAMMABLE GAS,IR,0TO100%LEL	{"fields": {"make": {"value": "TELEDYNE DETCON INC.", "quality": "Confirmed"}, "model": {"value": "HART-BRIDGE MODULE", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "USA", "quality": "Verify"}, "part_no": {"value": "9H303091-100M", "quality": "Confirmed"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "35-GDF-01A-007", "quality": "Confirmed"}, "description": {"value": "DETECTOR,FLAMMABLE GAS,IR,0TO100%LEL", "quality": "Confirmed"}, "size_dimension": {"value": "3/4 NPT", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "12", "quality": "Confirmed"}, "additional_information": {"value": "ADDRESS: 14880 SKINNER ROAD, CYPRESS, TEXAS 77429, VOLTAGE: 11.5-30VDC, CURRENT: 25mA @ 24VDC, AMBIENT TEMPERATURE RANGE: -40°C TO +75°C, CSA CERTIFIED, ENCLOSURE MARKING (second body): ALL CABLE ENTRIES ARE 3/4 NPT, D: Ex db IIB+H2 Gb, C1IB+H2 Gb, CLASS I GROUP B,C,D, AEx d IIB+H2 Gb, PART NO. 897-950000-010, M/Y: 10/2024, ENCLOSURE ONLY - SEE INSTALLATION INSTRUCTION DOCUMENT, ATTACHED FITTING LABEL: 927-215500-000 A0001Q2J", "quality": "Verify"}, "hazardous_classification": {"value": "CLASS I DIV 1 GROUPS B,C&D HAZARDOUS LOCATIONS; II 2 G Ex db IIB+H2 Gb, Tamb -40°C to +70°C; IECEX DEK 22.0060X; DEKRA 15 ATEX0025 X", "quality": "Confirmed"}}, "remarks": "Two separate red nameplates are visible: one on the sensor/transmitter head (HART-Bridge Module, dated 12/2024) and one on the enclosure body (dated 10/2024, part no. 897-950000-010). Serial number and weight are not printed on either plate. Country inferred from Texas, USA address on plate, not explicitly labeled 'Country'. Small white label near bottom fitting (927-215500-000 / A0001Q2J) may be a separate component tag, included under additional information for completeness. No tag number matching or differing from 35-GDF-01A-007 is printed on either plate; register value retained as instructed.", "qc_comment": "Two distinct nameplates photographed (module and enclosure); reconciled into one record. Recommend field verification of serial number, weight, and country, as these are not explicitly printed. Date codes on the two plates differ (12/2024 vs 10/2024) - used the sensor module plate (12/2024) as primary manufacture date; enclosure date noted in additional_information.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "TELEDYNE DETCON INC.", "quality": "Confirmed"}, "model": {"value": "HART-BRIDGE MODULE", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "USA", "quality": "Verify"}, "part_no": {"value": "9H303091-100M", "quality": "Confirmed"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "35-GDF-01A-007", "quality": "Confirmed"}, "description": {"value": "DETECTOR,FLAMMABLE GAS,IR,0TO100%LEL", "quality": "Confirmed"}, "size_dimension": {"value": "3/4 NPT", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "12", "quality": "Confirmed"}, "additional_information": {"value": "ADDRESS: 14880 SKINNER ROAD, CYPRESS, TEXAS 77429, VOLTAGE: 11.5-30VDC, CURRENT: 25mA @ 24VDC, AMBIENT TEMPERATURE RANGE: -40°C TO +75°C, CSA CERTIFIED, ENCLOSURE MARKING (second body): ALL CABLE ENTRIES ARE 3/4 NPT, D: Ex db IIB+H2 Gb, C1IB+H2 Gb, CLASS I GROUP B,C,D, AEx d IIB+H2 Gb, PART NO. 897-950000-010, M/Y: 10/2024, ENCLOSURE ONLY - SEE INSTALLATION INSTRUCTION DOCUMENT, ATTACHED FITTING LABEL: 927-215500-000 A0001Q2J", "quality": "Verify"}, "hazardous_classification": {"value": "CLASS I DIV 1 GROUPS B,C&D HAZARDOUS LOCATIONS; II 2 G Ex db IIB+H2 Gb, Tamb -40°C to +70°C; IECEX DEK 22.0060X; DEKRA 15 ATEX0025 X", "quality": "Confirmed"}}, "remarks": "Two separate red nameplates are visible: one on the sensor/transmitter head (HART-Bridge Module, dated 12/2024) and one on the enclosure body (dated 10/2024, part no. 897-950000-010). Serial number and weight are not printed on either plate. Country inferred from Texas, USA address on plate, not explicitly labeled 'Country'. Small white label near bottom fitting (927-215500-000 / A0001Q2J) may be a separate component tag, included under additional information for completeness. No tag number matching or differing from 35-GDF-01A-007 is printed on either plate; register value retained as instructed.", "qc_comment": "Two distinct nameplates photographed (module and enclosure); reconciled into one record. Recommend field verification of serial number, weight, and country, as these are not explicitly printed. Date codes on the two plates differ (12/2024 vs 10/2024) - used the sensor module plate (12/2024) as primary manufacture date; enclosure date noted in additional_information.", "photo_status": "MEDIUM"}	/data/storage/exports/35-GDF-01A-007/AI Output-35-GDF-01A-007-DETECTOR,FLAMMABLE GAS,IR,0TO100%LEL.xlsx	/data/storage/exports/35-GDF-01A-007/35-GDF-01A-007-DETECTOR,FLAMMABLE GAS,IR,0TO100%LEL-Template.xlsx	\N	3	1	2026-08-20 11:27:59.750715+00	2026-08-20 11:27:59.750715+00
53	12-GDF-03-0103	FLAMMABLE GAS DETECTOR	{"fields": {"make": {"value": "MSA (The Safety Company)", "quality": "Confirmed"}, "model": {"value": "Ultima X5000", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "MADE IN INDIA", "quality": "Verify"}, "part_no": {"value": "A-X5000-0-A-0-0-AC-00-0", "quality": "Confirmed"}, "serial_no": {"value": "000100000186015E", "quality": "Confirmed"}, "tag_number": {"value": "12-GDF-03-0103", "quality": "Confirmed"}, "description": {"value": "FLAMMABLE GAS DETECTOR", "quality": "Confirmed"}, "size_dimension": {"value": "3/4 NPT", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "06", "quality": "Confirmed"}, "additional_information": {"value": "RATED INPUT: 11-30 VDC, 1.3A (15W) MAX, CLASS 2/CLASS M, CABLE ENTRY: WITHIN 15 INCHES (450mm), CABLE SEAL REQUIRED, TEMP RANGE: -40°C ≤ Ta ≤ +60°C, FM APPROVED US: FM21CA0073X, FM G21.0021X, ASSEMBLED IN IRELAND: GENERAL MONITORS, BALLYBRIT BUSINESS PARK, GALWAY H91 H6P2 IRELAND, PRODUCT OF U.S., ASSEMBLED IN U.S.: MSA THE SAFETY COMPANY, 1000 CRANBERRY WOODS DRIVE, CRANBERRY TWP, PA 16066 USA, WARNING: DO NOT OPEN WHEN ENERGIZED OR WHEN EXPLOSIVE ATMOSPHERE PRESENT (bilingual EN/FR)", "quality": "Verify"}, "hazardous_classification": {"value": "Ex nA IIC T4 Gc, II 3G, FM21ATEX0073X, IECEx FMG21.0021X, FM21UKEX0220X, Enclosure: Type 4X, IP66", "quality": "Verify"}}, "remarks": "Second photo shows slightly different certificate suffixes (FM21ATEX0071X, IECEx FMG21.0021X, FM21UKEX0216X) versus the first photo's tag (FM21ATEX0073X, FM21UKEX0220X) — likely from a different section of the same unit or a printing variance; verify against physical unit. Country of origin is ambiguous: a separate 'MADE IN INDIA' label is affixed near the mounting bracket, while the printed nameplate itself states 'Assembled in Ireland' and 'Product of U.S.' / 'Assembled in U.S.' — this conflict should be checked in person. No tag number or equipment description is printed on the plate itself; both were taken from the asset register as instructed. Weight not stated on nameplate.", "qc_comment": "Core identification data (model, serial, part number, date code, hazardous marking) legible and consistent across both photos, but country-of-origin labeling is contradictory and hazardous certificate suffixes differ slightly between the two images — recommend manual verification of these two points before finalizing the asset record.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "MSA (The Safety Company)", "quality": "Confirmed"}, "model": {"value": "Ultima X5000", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "MADE IN INDIA", "quality": "Verify"}, "part_no": {"value": "A-X5000-0-A-0-0-AC-00-0", "quality": "Confirmed"}, "serial_no": {"value": "000100000186015E", "quality": "Confirmed"}, "tag_number": {"value": "12-GDF-03-0103", "quality": "Confirmed"}, "description": {"value": "FLAMMABLE GAS DETECTOR", "quality": "Confirmed"}, "size_dimension": {"value": "3/4 NPT", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "06", "quality": "Confirmed"}, "additional_information": {"value": "RATED INPUT: 11-30 VDC, 1.3A (15W) MAX, CLASS 2/CLASS M, CABLE ENTRY: WITHIN 15 INCHES (450mm), CABLE SEAL REQUIRED, TEMP RANGE: -40°C ≤ Ta ≤ +60°C, FM APPROVED US: FM21CA0073X, FM G21.0021X, ASSEMBLED IN IRELAND: GENERAL MONITORS, BALLYBRIT BUSINESS PARK, GALWAY H91 H6P2 IRELAND, PRODUCT OF U.S., ASSEMBLED IN U.S.: MSA THE SAFETY COMPANY, 1000 CRANBERRY WOODS DRIVE, CRANBERRY TWP, PA 16066 USA, WARNING: DO NOT OPEN WHEN ENERGIZED OR WHEN EXPLOSIVE ATMOSPHERE PRESENT (bilingual EN/FR)", "quality": "Verify"}, "hazardous_classification": {"value": "Ex nA IIC T4 Gc, II 3G, FM21ATEX0073X, IECEx FMG21.0021X, FM21UKEX0220X, Enclosure: Type 4X, IP66", "quality": "Verify"}}, "remarks": "Second photo shows slightly different certificate suffixes (FM21ATEX0071X, IECEx FMG21.0021X, FM21UKEX0216X) versus the first photo's tag (FM21ATEX0073X, FM21UKEX0220X) — likely from a different section of the same unit or a printing variance; verify against physical unit. Country of origin is ambiguous: a separate 'MADE IN INDIA' label is affixed near the mounting bracket, while the printed nameplate itself states 'Assembled in Ireland' and 'Product of U.S.' / 'Assembled in U.S.' — this conflict should be checked in person. No tag number or equipment description is printed on the plate itself; both were taken from the asset register as instructed. Weight not stated on nameplate.", "qc_comment": "Core identification data (model, serial, part number, date code, hazardous marking) legible and consistent across both photos, but country-of-origin labeling is contradictory and hazardous certificate suffixes differ slightly between the two images — recommend manual verification of these two points before finalizing the asset record.", "photo_status": "MEDIUM"}	/data/storage/exports/12-GDF-03-0103/AI Output-12-GDF-03-0103-FLAMMABLE GAS DETECTOR.xlsx	/data/storage/exports/12-GDF-03-0103/12-GDF-03-0103-FLAMMABLE GAS DETECTOR-Template.xlsx	\N	3	1	2026-08-19 11:10:20.185873+00	2026-08-19 11:10:20.185873+00
73	2196JAM-CSS	PUSH BUTTON STATION	{"fields": {"make": {"value": "GOVAN", "quality": "Confirmed"}, "model": {"value": "404/E7-LCS", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "AUS", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "200843-212", "quality": "Confirmed"}, "tag_number": {"value": "2196JAM-CSS", "quality": "Confirmed"}, "description": {"value": "PUSH BUTTON STATION", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "FAA No: 613 9458 1109, VOLTS: 240, AMPS: 3, WARNING: ISOLATE CIRCUIT ELSEWHERE BEFORE OPENING COVER", "quality": "Verify"}, "hazardous_classification": {"value": "EX D IIB T6, AUS EX, IP66", "quality": "Verify"}}, "remarks": "FAA No. digits partially worn/glared (read as 613 9458 1109, low confidence on some digits). TYPE field shows '404' and 'E7-LCS' stacked - interpreted as combined model code, but exact relationship unclear. No year/month, size, part number, or weight printed on plate. Country inferred from 'AUS Ex' marking rather than explicit country field.", "qc_comment": "Core identification (make, serial no, hazardous classification) clearly legible; several fields absent from plate and FAA number partially obscured by glare/wear - recommend physical verification if critical.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "GOVAN", "quality": "Confirmed"}, "model": {"value": "404/E7-LCS", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "AUS", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "200843-212", "quality": "Confirmed"}, "tag_number": {"value": "2196JAM-CSS", "quality": "Confirmed"}, "description": {"value": "PUSH BUTTON STATION", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "FAA No: 613 9458 1109, VOLTS: 240, AMPS: 3, WARNING: ISOLATE CIRCUIT ELSEWHERE BEFORE OPENING COVER", "quality": "Verify"}, "hazardous_classification": {"value": "EX D IIB T6, AUS EX, IP66", "quality": "Verify"}}, "remarks": "FAA No. digits partially worn/glared (read as 613 9458 1109, low confidence on some digits). TYPE field shows '404' and 'E7-LCS' stacked - interpreted as combined model code, but exact relationship unclear. No year/month, size, part number, or weight printed on plate. Country inferred from 'AUS Ex' marking rather than explicit country field.", "qc_comment": "Core identification (make, serial no, hazardous classification) clearly legible; several fields absent from plate and FAA number partially obscured by glare/wear - recommend physical verification if critical.", "photo_status": "MEDIUM"}	/data/storage/exports/2196JAM-CSS/AI Output-2196JAM-CSS-PUSH BUTTON STATION.xlsx	/data/storage/exports/2196JAM-CSS/2196JAM-CSS-PUSH BUTTON STATION-Template.xlsx	\N	3	1	2026-08-20 11:29:55.052797+00	2026-08-20 11:29:55.052797+00
54	12-M2-DBV-0002	DOUBLE BLOCK AND BLEED VALVE	{"fields": {"make": {"value": "ASTEC", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "778558.990.1M", "quality": "Verify"}, "serial_no": {"value": "DC1633", "quality": "Confirmed"}, "tag_number": {"value": "12-M2-DBV-0002", "quality": "Confirmed"}, "description": {"value": "DOUBLE BLOCK AND BLEED VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\" ASME 1500#, VALVE BORE: 10MM", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "02", "quality": "Confirmed"}, "additional_information": {"value": "CUSTOMER: AXIOM INTERNATIONAL, PO: PO-ASTEC-SO-6371-AK-74587, VALVE TYPE: INTEGRAL DOUBLE BLOCK & BLEED VALVE, BODY MOC (NACE): ASTM A182 GR. F316, TRIM MOC (NACE): ASTM A182 GR. F316, SEAT MOC: PEEK, DESIGN PRESSURE: 248.2 BARG @ 38°C, DESIGN TEMPERATURE: -50°C TO 150°C, HYDRO (SHELL): 372.5 BARG, HYDRO (SEAT): 273.5 BARG, PNEU (SEAT): 7 BARG, HEAT NO.: A-9596, DESIGN CODE: ASME B16.34 / ISO 17292 / EEMUA 182, HEAT TREATMENT: SOLUTION ANNEALED", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Manufacturer name on logo is stylised ('as[symbol]tec') and partially obscured by dirt/scratches - transcribed as ASTEC but should be verified against catalogue. A separate hanging metal ID tag shows a tag number similar to the register value but partially worn/glared ('12-M2-DBV-0??2'); could not fully confirm the last digits match the register tag '12-M2-DBV-0002' - recommend physical verification. MESC number used as part number in absence of a dedicated 'Part No.' field on plate.", "qc_comment": "Both nameplate photos are reasonably clear and consistent; main uncertainty is the manufacturer logo legibility and the worn hanging ID tag number, both flagged for verification.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "ASTEC VALVES AND FITTING", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "778558.990.1M", "quality": "Verify"}, "serial_no": {"value": "DC1633", "quality": "Confirmed"}, "tag_number": {"value": "12-M2-DBV-0002", "quality": "Confirmed"}, "description": {"value": "DOUBLE BLOCK AND BLEED VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\" ASME 1500#, VALVE BORE: 10MM", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "02", "quality": "Confirmed"}, "additional_information": {"value": "CUSTOMER: AXIOM INTERNATIONAL, PO: PO-ASTEC-SO-6371-AK-74587, VALVE TYPE: INTEGRAL DOUBLE BLOCK & BLEED VALVE, BODY MOC (NACE): ASTM A182 GR. F316, TRIM MOC (NACE): ASTM A182 GR. F316, SEAT MOC: PEEK, DESIGN PRESSURE: 248.2 BARG @ 38°C, DESIGN TEMPERATURE: -50°C TO 150°C, HYDRO (SHELL): 372.5 BARG, HYDRO (SEAT): 273.5 BARG, PNEU (SEAT): 7 BARG, HEAT NO.: A-9596, DESIGN CODE: ASME B16.34 / ISO 17292 / EEMUA 182, HEAT TREATMENT: SOLUTION ANNEALED", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Manufacturer name on logo is stylised ('as[symbol]tec') and partially obscured by dirt/scratches - transcribed as ASTEC but should be verified against catalogue. A separate hanging metal ID tag shows a tag number similar to the register value but partially worn/glared ('12-M2-DBV-0??2'); could not fully confirm the last digits match the register tag '12-M2-DBV-0002' - recommend physical verification. MESC number used as part number in absence of a dedicated 'Part No.' field on plate.", "qc_comment": "Both nameplate photos are reasonably clear and consistent; main uncertainty is the manufacturer logo legibility and the worn hanging ID tag number, both flagged for verification.", "photo_status": "MEDIUM"}	/data/storage/exports/12-M2-DBV-0002/AI Output-12-M2-DBV-0002-DOUBLE BLOCK AND BLEED VALVE.xlsx	/data/storage/exports/12-M2-DBV-0002/12-M2-DBV-0002-DOUBLE BLOCK AND BLEED VALVE-Template.xlsx	3	3	2	2026-08-19 11:15:45.845526+00	2026-08-19 11:18:42.429825+00
55	12-M2-GV-0038	GATE VALVE	{"fields": {"make": {"value": "FB VALVE", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "FV24082201111", "quality": "Verify"}, "tag_number": {"value": "12-M2-GV-0038", "quality": "Confirmed"}, "description": {"value": "GATE VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 6, CLASS 900", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "12", "quality": "Confirmed"}, "additional_information": {"value": "STANDARD: API 600, DESIGN STD: ASME B16.34, MANUFACTURING SPEC: API 624, BODY: WCB, WEDGE: WCB+STL6, SEAT: A105N+STL6, STEM: 316/316L SPE, OP.TEMP: 16.9 MPa@ 38 C, F TO F: 610±1.5, WEBSITE: www.fbvalve.com, DATE OF MFG: 2024.12", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Serial number partially unclear due to glare/angle - transcribed as FV24082201111 but final digits should be verified against physical plate. Manufacturer 'FB VALVE' inferred from logo and website URL (www.fbvalve.com), no explicit 'MAKE' label present. No hazardous area classification, weight, part number, model, or country of origin printed on this valve nameplate - this is a standard mechanical valve tag without electrical/ATEX markings. Tag number and description confirmed from asset register match expected equipment type (gate valve).", "qc_comment": "Plate is legible overall but partial glare on serial number digits and slight tilt of camera angle warrant a second visual check on-site. All critical technical specs (class, size, body material, date of manufacture) are clearly confirmed.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "FB VALVE", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "FV24082201111", "quality": "Verify"}, "tag_number": {"value": "12-M2-GV-0038", "quality": "Confirmed"}, "description": {"value": "GATE VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 6, CLASS 900", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "12", "quality": "Confirmed"}, "additional_information": {"value": "STANDARD: API 600, DESIGN STD: ASME B16.34, MANUFACTURING SPEC: API 624, BODY: WCB, WEDGE: WCB+STL6, SEAT: A105N+STL6, STEM: 316/316L SPE, OP.TEMP: 16.9 MPa@ 38 C, F TO F: 610±1.5, WEBSITE: www.fbvalve.com, DATE OF MFG: 2024.12", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Serial number partially unclear due to glare/angle - transcribed as FV24082201111 but final digits should be verified against physical plate. Manufacturer 'FB VALVE' inferred from logo and website URL (www.fbvalve.com), no explicit 'MAKE' label present. No hazardous area classification, weight, part number, model, or country of origin printed on this valve nameplate - this is a standard mechanical valve tag without electrical/ATEX markings. Tag number and description confirmed from asset register match expected equipment type (gate valve).", "qc_comment": "Plate is legible overall but partial glare on serial number digits and slight tilt of camera angle warrant a second visual check on-site. All critical technical specs (class, size, body material, date of manufacture) are clearly confirmed.", "photo_status": "MEDIUM"}	/data/storage/exports/12-M2-GV-0038/AI Output-12-M2-GV-0038-GATE VALVE.xlsx	/data/storage/exports/12-M2-GV-0038/12-M2-GV-0038-GATE VALVE-Template.xlsx	\N	3	1	2026-08-19 11:15:56.892006+00	2026-08-19 11:15:56.892006+00
74	73-PV-029	VALVE,CONTROL,PRESSURE2IN	{"fields": {"make": {"value": "DRESSER MASONEILAN", "quality": "Confirmed"}, "model": {"value": "88-2115", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "S 398760-49", "quality": "Verify"}, "tag_number": {"value": "73-PV-029", "quality": "Confirmed"}, "description": {"value": "VALVE,CONTROL,PRESSURE2IN", "quality": "Confirmed"}, "size_dimension": {"value": "2 INCH", "quality": "Confirmed"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "ACTION: AIR TO OPEN, CV: 46, RANGE: 11-23 PSI, SUPPLY: 23 PSI, BODY MAT'L: A216, STEM MAT'L: A564, PLUG/DISC MAT'L: 416 SS, SEAT MAT'L: 416 SS, RATING: ANSI 300 B16.34, DRAWING NO: 983750-001", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Tag number on plate (73-PV-029) matches asset register, no mismatch. Model number and serial number partially obscured by glare/wear, best-effort reading provided. Supply pressure figure partly glared, read as 23 PSI. Drawing number at lower left edge partially worn, read as 983750-001. No country, weight, date-of-manufacture, or hazardous area classification printed on this plate.", "qc_comment": "Recommend physical verification of model number, serial number, and supply pressure due to glare and surface wear on the stainless plate.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "DRESSER MASONEILAN", "quality": "Confirmed"}, "model": {"value": "88-2115", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "S 398760-49", "quality": "Verify"}, "tag_number": {"value": "73-PV-029", "quality": "Confirmed"}, "description": {"value": "VALVE,CONTROL,PRESSURE2IN", "quality": "Confirmed"}, "size_dimension": {"value": "2 INCH", "quality": "Confirmed"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "ACTION: AIR TO OPEN, CV: 46, RANGE: 11-23 PSI, SUPPLY: 23 PSI, BODY MAT'L: A216, STEM MAT'L: A564, PLUG/DISC MAT'L: 416 SS, SEAT MAT'L: 416 SS, RATING: ANSI 300 B16.34, DRAWING NO: 983750-001", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Tag number on plate (73-PV-029) matches asset register, no mismatch. Model number and serial number partially obscured by glare/wear, best-effort reading provided. Supply pressure figure partly glared, read as 23 PSI. Drawing number at lower left edge partially worn, read as 983750-001. No country, weight, date-of-manufacture, or hazardous area classification printed on this plate.", "qc_comment": "Recommend physical verification of model number, serial number, and supply pressure due to glare and surface wear on the stainless plate.", "photo_status": "MEDIUM"}	/data/storage/exports/73-PV-029/AI Output-73-PV-029-VALVE,CONTROL,PRESSURE2IN.xlsx	/data/storage/exports/73-PV-029/73-PV-029-VALVE,CONTROL,PRESSURE2IN-Template.xlsx	\N	3	1	2026-08-20 11:30:05.961083+00	2026-08-20 11:30:05.961083+00
30	12-4020-BV-0074	BALL VALVE	{"fields": {"make": {"value": "JC", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "22224-70-278", "quality": "Confirmed"}, "tag_number": {"value": "12-4020-BV-0074", "quality": "Confirmed"}, "description": {"value": "BALL VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\"X3/4\\"1500#", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "10", "quality": "Confirmed"}, "additional_information": {"value": "API 607 B16.10, ISO 17292, BODY: LF2, SEAT: PEEK, STEM: F316(L), BALL: F316(L), RATING 1: 255.3 bar -50/38°C, RATING 2: 238.6 bar 84°C", "quality": "Confirmed"}, "hazardous_classification": {"value": "II 2GD LCIE 05 AR 023", "quality": "Confirmed"}}, "remarks": "Date code 10/24 transcribed as month 10, year 2024. Make read from manufacturer logo.", "qc_comment": "All fields legible directly from nameplate photo.", "photo_status": "EASY"}	{"fields": {"make": {"value": "JC", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "22224-70-278", "quality": "Confirmed"}, "tag_number": {"value": "12-4020-BV-0074", "quality": "Confirmed"}, "description": {"value": "BALL VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 1\\"X3/4\\"1500#", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "10", "quality": "Confirmed"}, "additional_information": {"value": "API 607 B16.10, ISO 17292, BODY: LF2, SEAT: PEEK, STEM: F316(L), BALL: F316(L), RATING 1: 255.3 bar -50/38°C, RATING 2: 238.6 bar 84°C", "quality": "Confirmed"}, "hazardous_classification": {"value": "II 2GD LCIE 05 AR 023", "quality": "Confirmed"}}, "remarks": "Date code 10/24 transcribed as month 10, year 2024. Make read from manufacturer logo.", "qc_comment": "All fields legible directly from nameplate photo.", "photo_status": "EASY"}	/data/storage/exports/12-4020-BV-0074/AI Output-12-4020-BV-0074-BALL VALVE.xlsx	/data/storage/exports/12-4020-BV-0074/12-4020-BV-0074-BALL VALVE-Template.xlsx	\N	2	1	2026-08-17 10:02:15.986022+00	2026-08-17 10:02:15.986022+00
33	54-038-P12	EXTINGUISHER,DRY POWDER	{"fields": {"make": {"value": "INTERNATIONAL GULF TRADING COMPANY - FIRE EXTINGUISHER DIVISION", "quality": "Confirmed"}, "model": {"value": "P9", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "QATAR", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "54-038-P12", "quality": "Confirmed"}, "description": {"value": "EXTINGUISHER,DRY POWDER", "quality": "Confirmed"}, "size_dimension": {"value": "9 KG", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2023", "quality": "Confirmed"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "BRAND: ORYX FIRE, EXTINGUISHING MEDIUM: 9kg 40% ABC Dry Chemical Powder, PROPELLANT GAS: Dry Nitrogen, TEST PRESSURE: 27 bar, OPERATING PRESSURE: 14 bar at 20°C, TEMPERATURE RANGE: -30°C to +60°C, RATING: 43A - 233B - C, CERTIFICATION: BS EN3 (Kitemark No. 671501), CE MARK: CE 2797", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Extinguisher capacity is 9 kg dry powder. Serial number not printed on label. Brand is ORYX FIRE, manufactured by IGTC.", "qc_comment": "All data clearly legible from the provided labels.", "photo_status": "EASY"}	{"fields": {"make": {"value": "INTERNATIONAL GULF TRADING COMPANY - FIRE EXTINGUISHER DIVISION", "quality": "Confirmed"}, "model": {"value": "P9", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "QATAR", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "54-038-P12", "quality": "Confirmed"}, "description": {"value": "EXTINGUISHER,DRY POWDER", "quality": "Confirmed"}, "size_dimension": {"value": "9 KG", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2023", "quality": "Confirmed"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "BRAND: ORYX FIRE, EXTINGUISHING MEDIUM: 9kg 40% ABC Dry Chemical Powder, PROPELLANT GAS: Dry Nitrogen, TEST PRESSURE: 27 bar, OPERATING PRESSURE: 14 bar at 20°C, TEMPERATURE RANGE: -30°C to +60°C, RATING: 43A - 233B - C, CERTIFICATION: BS EN3 (Kitemark No. 671501), CE MARK: CE 2797", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Extinguisher capacity is 9 kg dry powder. Serial number not printed on label. Brand is ORYX FIRE, manufactured by IGTC.", "qc_comment": "All data clearly legible from the provided labels.", "photo_status": "EASY"}	/data/storage/exports/54-038-P12/AI Output-54-038-P12-EXTINGUISHER,DRY POWDER.xlsx	/data/storage/exports/54-038-P12/54-038-P12-EXTINGUISHER,DRY POWDER-Template.xlsx	\N	2	1	2026-08-17 10:41:51.6822+00	2026-08-17 10:41:51.6822+00
32	74-FG-024	GAUGE,SIGHT GLASS	{"fields": {"make": {"value": "SAMIL INDUSTRY CO., LTD.", "quality": "Confirmed"}, "model": {"value": "SSG-1FB", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "KOREA", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "05020492", "quality": "Confirmed"}, "tag_number": {"value": "74-FG-024", "quality": "Confirmed"}, "description": {"value": "GAUGE,SIGHT GLASS", "quality": "Confirmed"}, "size_dimension": {"value": "3/4\\" 300RF", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2005", "quality": "Confirmed"}, "month_of_manufacture": {"value": "02", "quality": "Confirmed"}, "additional_information": {"value": "MAT'L: A 216 WCB, ADDRESS: INCHEON, KOREA TEL: 032)819-9671", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Date field read as 2005.02 representing February 2005.", "qc_comment": "Nameplate is fully legible and matches register tag number.", "photo_status": "EASY"}	{"fields": {"make": {"value": "SAMIL INDUSTRY CO., LTD.", "quality": "Confirmed"}, "model": {"value": "SSG-1FB", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "KOREA", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "05020492", "quality": "Confirmed"}, "tag_number": {"value": "74-FG-024", "quality": "Confirmed"}, "description": {"value": "GAUGE,SIGHT GLASS", "quality": "Confirmed"}, "size_dimension": {"value": "3/4INCH 300RF", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2005", "quality": "Confirmed"}, "month_of_manufacture": {"value": "02", "quality": "Confirmed"}, "additional_information": {"value": "MATERIAL: ASTM 216 WCB", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Date field read as 2005.02 representing February 2005.", "qc_comment": "Nameplate is fully legible and matches register tag number.", "photo_status": "EASY"}	/data/storage/exports/74-FG-024/AI Output-74-FG-024-GAUGE,SIGHT GLASS.xlsx	/data/storage/exports/74-FG-024/74-FG-024-GAUGE,SIGHT GLASS-Template.xlsx	2	2	2	2026-08-17 10:40:57.038969+00	2026-08-17 10:46:03.723937+00
34	71-FV-003	VALVE,CONTROL,FLOW	{"fields": {"make": {"value": "Masoneilan", "quality": "Confirmed"}, "model": {"value": "70-35612", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "S 398760-143", "quality": "Confirmed"}, "tag_number": {"value": "71-FV-003", "quality": "Confirmed"}, "description": {"value": "VALVE,CONTROL,FLOW", "quality": "Confirmed"}, "size_dimension": {"value": "6 INCH", "quality": "Confirmed"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "ACTION: AIR TO OPEN, SUPPLY: 35 PSI, MAT'L BODY: A216, MAT'L STEM: A564, MAT'L PLUG: 316 HF, MAT'L SEAT: 316 HF, RATING: ANSI 300 B16.34, PART NO: 943750-001", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "", "qc_comment": "Nameplate details transcribed successfully. Worn/weathered surface partially obscures ACTION and RANGE fields.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "Masoneilan", "quality": "Confirmed"}, "model": {"value": "70-35612", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "S 398760-143", "quality": "Confirmed"}, "tag_number": {"value": "71-FV-003", "quality": "Confirmed"}, "description": {"value": "VALVE,CONTROL,FLOW", "quality": "Confirmed"}, "size_dimension": {"value": "6 INCH", "quality": "Confirmed"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "ACTION: AIR TO OPEN, SUPPLY: 35 PSI, MAT'L BODY: A216, MAT'L STEM: A564, MAT'L PLUG: 316 HF, MAT'L SEAT: 316 HF, RATING: ANSI 300 B16.34, PART NO: 943750-001", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "", "qc_comment": "Nameplate details transcribed successfully. Worn/weathered surface partially obscures ACTION and RANGE fields.", "photo_status": "MEDIUM"}	/data/storage/exports/71-FV-003/AI Output-71-FV-003-VALVE,CONTROL,FLOW.xlsx	/data/storage/exports/71-FV-003/71-FV-003-VALVE,CONTROL,FLOW-Template.xlsx	\N	2	1	2026-08-17 10:42:03.582937+00	2026-08-17 10:42:03.582937+00
56	12-M2-PIT-0001	PRESSURE TRANSMITTER	{"fields": {"make": {"value": "ROSEMOUNT (Emerson FZE, Dubai, UAE)", "quality": "Confirmed"}, "model": {"value": "3051TG4F2B81BS5BEK8Y2M5Q4Q8Q76T1P1Q15", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "UAE", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "24DUPG5030948", "quality": "Confirmed"}, "tag_number": {"value": "12-M2-PIT-0001", "quality": "Confirmed"}, "description": {"value": "PRESSURE TRANSMITTER", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2025", "quality": "Verify"}, "month_of_manufacture": {"value": "01", "quality": "Verify"}, "additional_information": {"value": "TYPE: 111, SW: 1.0.1, HW: 1.0.1, MAX W.P.: 4000PSI/276BAR, CAL: 0 TO 110 BAR G, HART 4-20mA SUPPLY: 10.5-30V, FOUNDATION FIELDBUS SUPPLY: 9-30V 17.5mA (selected X), PROFIBUS-PA: not selected, INTEGRAL MANIFOLD MODEL: 0306RT22BA11SG, FOUNDATION FIELDBUS CERTIFIED MARK PRESENT", "quality": "Verify"}, "hazardous_classification": {"value": "Ex ia IIC T4 Ga, SEE CERTIFICATE BAS97ATEX1069X; Ex ta IIIC T105°C (-20°C ≤ Ta ≤ 85°C) Baseefa11ATEX0275X; ATEX II 1D; CE marked; EAC; CSA (C/US)", "quality": "Verify"}}, "remarks": "Serial No., Model, MAX W.P., CAL range, and SW/HW versions clearly read from Photo 3. Date code '01/25' seen on Photos 1 & 2 interpreted as month 01/year 2025 per rule 5. Hazardous classification text partially obscured by corrosion/debris in Photo 2 but core ATEX/CSA/EAC markings legible. Tag number on plate not fully visible due to corrosion/fibrous debris covering upper label area, but partial '12-M2-PIT-0001' visible in Photo 1 matches register tag - no mismatch noted. No separate 'Part No.' or weight field printed on plate.", "qc_comment": "Nameplate is heavily obscured by corrosion and rust-colored fibrous debris across the top section in Photos 1 and 2, obscuring some hazardous area classification text. Photo 3 provides clear, well-lit close-up of serial, model, and rating details. Cross-referenced all three images to reconcile readings; recommend a human verify the exact date code and hazardous classification wording against a cleaned plate if possible.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "ROSEMOUNT (Emerson FZE, Dubai, UAE)", "quality": "Confirmed"}, "model": {"value": "3051TG4F2B81BS5BEK8Y2M5Q4Q8Q76T1P1Q15", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "UAE", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "24DUPG5030948", "quality": "Confirmed"}, "tag_number": {"value": "12-M2-PIT-0001", "quality": "Confirmed"}, "description": {"value": "PRESSURE TRANSMITTER", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "01", "quality": "Confirmed"}, "additional_information": {"value": "TYPE: 111, SW: 1.0.1, HW: 1.0.1, MAX W.P.: 4000PSI/276BAR, CAL: 0 TO 110 BAR G, HART 4-20mA SUPPLY: 10.5-30V, FOUNDATION FIELDBUS SUPPLY: 9-30V 17.5mA (selected X), PROFIBUS-PA: not selected, INTEGRAL MANIFOLD MODEL: 0306RT22BA11SG, FOUNDATION FIELDBUS CERTIFIED MARK PRESENT", "quality": "Verify"}, "hazardous_classification": {"value": "Ex ia IIC T4 Ga, SEE CERTIFICATE BAS97ATEX1069X; Ex ta IIIC T105°C (-20°C ≤ Ta ≤ 85°C) Baseefa11ATEX0275X; ATEX II 1D; CE marked; EAC; CSA (C/US)", "quality": "Verify"}}, "remarks": "Serial No., Model, MAX W.P., CAL range, and SW/HW versions clearly read from Photo 3. Date code '01/25' seen on Photos 1 & 2 interpreted as month 01/year 2025 per rule 5. Hazardous classification text partially obscured by corrosion/debris in Photo 2 but core ATEX/CSA/EAC markings legible. Tag number on plate not fully visible due to corrosion/fibrous debris covering upper label area, but partial '12-M2-PIT-0001' visible in Photo 1 matches register tag - no mismatch noted. No separate 'Part No.' or weight field printed on plate.", "qc_comment": "Nameplate is heavily obscured by corrosion and rust-colored fibrous debris across the top section in Photos 1 and 2, obscuring some hazardous area classification text. Photo 3 provides clear, well-lit close-up of serial, model, and rating details. Cross-referenced all three images to reconcile readings; recommend a human verify the exact date code and hazardous classification wording against a cleaned plate if possible.", "photo_status": "MEDIUM"}	/data/storage/exports/12-M2-PIT-0001/AI Output-12-M2-PIT-0001-PRESSURE TRANSMITTER.xlsx	/data/storage/exports/12-M2-PIT-0001/12-M2-PIT-0001-PRESSURE TRANSMITTER-Template.xlsx	3	3	2	2026-08-19 11:36:28.331076+00	2026-08-19 11:39:17.002436+00
57	12-M2-PIT	0008 ELECTRONIC PRESSURE TRANSMITTER	{"fields": {"make": {"value": "ROSEMOUNT", "quality": "Confirmed"}, "model": {"value": "3051TG4F2B81BS5BEK8Y2M5Q4Q8Q76T1P1Q15", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "UAE (Dubai)", "quality": "Verify"}, "part_no": {"value": "0306RT22BA11SG", "quality": "Verify"}, "serial_no": {"value": "24DUPG5030955", "quality": "Confirmed"}, "tag_number": {"value": "12-M2-PIT", "quality": "Confirmed"}, "description": {"value": "0008 ELECTRONIC PRESSURE TRANSMITTER", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "01", "quality": "Confirmed"}, "additional_information": {"value": "TYPE: 111, MAX W.P.: 4000PSI/276BAR, CAL: 0 TO 110 BAR G, HART SUPPLY: 4-20mA 10.5-30V, FOUNDATION FIELDBUS SUPPLY: 9-30V 17.5mA, PROFIBUS PA: present, INTEGRAL MANIFOLD MODEL: 0306RT22BA11SG, SW: 1.0.1, HW: 1.0.1, MANUFACTURER LOCATION: Emerson FZE, Dubai, UAE, MARKS: CE, EAC, CSAus", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Date code '01/25' interpreted as month 01, year 2025 per convention. Manifold model number (0306RT22BA11SG) used as part_no since no separate 'Part No.' field is printed; verify if a distinct part number exists elsewhere. No explicit hazardous area/ATEX/IECEx certificate marking visible on plate—only CE, EAC, and CSAus logos, so classification field left as not present. Weight and size/dimension not printed on plate. Country inferred from manufacturer's stated location (Dubai, UAE) rather than an explicit 'Country of Origin' field.", "qc_comment": "Two overlapping images allowed cross-verification of serial number, model, and date code; some text partially obscured by fibrous debris near housing base but key data fields remained legible.", "photo_status": "MEDIUM"}	{"fields": {"make": {"value": "ROSEMOUNT", "quality": "Confirmed"}, "model": {"value": "3051TG4F2B81BS5BEK8Y2M5Q4Q8Q76T1P1Q15", "quality": "Confirmed"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "UAE (Dubai)", "quality": "Verify"}, "part_no": {"value": "0306RT22BA11SG", "quality": "Verify"}, "serial_no": {"value": "24DUPG5030955", "quality": "Confirmed"}, "tag_number": {"value": "12-M2-PIT", "quality": "Confirmed"}, "description": {"value": "0008 ELECTRONIC PRESSURE TRANSMITTER", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2025", "quality": "Confirmed"}, "month_of_manufacture": {"value": "01", "quality": "Confirmed"}, "additional_information": {"value": "TYPE: 111, MAX W.P.: 4000PSI/276BAR, CAL: 0 TO 110 BAR G, HART SUPPLY: 4-20mA 10.5-30V, FOUNDATION FIELDBUS SUPPLY: 9-30V 17.5mA, PROFIBUS PA: present, INTEGRAL MANIFOLD MODEL: 0306RT22BA11SG, SW: 1.0.1, HW: 1.0.1, MANUFACTURER LOCATION: Emerson FZE, Dubai, UAE, MARKS: CE, EAC, CSAus", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Date code '01/25' interpreted as month 01, year 2025 per convention. Manifold model number (0306RT22BA11SG) used as part_no since no separate 'Part No.' field is printed; verify if a distinct part number exists elsewhere. No explicit hazardous area/ATEX/IECEx certificate marking visible on plate—only CE, EAC, and CSAus logos, so classification field left as not present. Weight and size/dimension not printed on plate. Country inferred from manufacturer's stated location (Dubai, UAE) rather than an explicit 'Country of Origin' field.", "qc_comment": "Two overlapping images allowed cross-verification of serial number, model, and date code; some text partially obscured by fibrous debris near housing base but key data fields remained legible.", "photo_status": "MEDIUM"}	/data/storage/exports/12-M2-PIT/AI Output-12-M2-PIT-0008 ELECTRONIC PRESSURE TRANSMITTER.xlsx	/data/storage/exports/12-M2-PIT/12-M2-PIT-0008 ELECTRONIC PRESSURE TRANSMITTER-Template.xlsx	\N	2	1	2026-08-19 11:39:29.029762+00	2026-08-19 11:39:29.029762+00
35	72-SSC-7203	SAMPLE COOLER	{"fields": {"make": {"value": "SEOCHANG IND. CO., LTD.", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "72-SSC-7203", "quality": "Confirmed"}, "description": {"value": "SAMPLE COOLER", "quality": "Confirmed"}, "size_dimension": {"value": "ANSI 300LB 3/4\\"", "quality": "Confirmed"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "DESIGN TEMP: 205 °C, PRESS.: 29.5 Bar G, SHELL MAT'L: A53 GR B-W, COIL MAT'L: A106 GR B, TEL: 031-988-2114", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "DATE field on nameplate is left blank. Manufacturer name read as SEOCHANG IND. CO., LTD. with SC VALVE logo.", "qc_comment": "All stamped details read successfully from clear nameplate.", "photo_status": "EASY"}	{"fields": {"make": {"value": "SEOCHANG IND. CO., LTD.", "quality": "Confirmed"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "72-SSC-7203", "quality": "Confirmed"}, "description": {"value": "SAMPLE COOLER", "quality": "Confirmed"}, "size_dimension": {"value": "ANSI 300LB 3/4\\"", "quality": "Confirmed"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "DESIGN TEMP: 205 °C, PRESS.: 29.5 Bar G, SHELL MAT'L: A53 GR B-W, COIL MAT'L: A106 GR B, TEL: 031-988-2114", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "DATE field on nameplate is left blank. Manufacturer name read as SEOCHANG IND. CO., LTD. with SC VALVE logo.", "qc_comment": "All stamped details read successfully from clear nameplate.", "photo_status": "EASY"}	/data/storage/exports/72-SSC-7203/AI Output-72-SSC-7203-SAMPLE COOLER.xlsx	/data/storage/exports/72-SSC-7203/72-SSC-7203-SAMPLE COOLER-Template.xlsx	\N	2	1	2026-08-17 10:42:27.358846+00	2026-08-17 10:42:27.358846+00
36	73-BV-0023	VALVE,BALL	{"fields": {"make": {"value": "KPT Corporation", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "KOREA", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "73-BV-0023", "quality": "Confirmed"}, "description": {"value": "VALVE,BALL", "quality": "Confirmed"}, "size_dimension": {"value": "2\\" 150#", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "BODY/BONNET: WCB", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate is severely corroded, rusted, and heavily weathered. Most stamped data fields including serial number, model, and date of manufacture are illegible.", "qc_comment": "Heavy surface corrosion severely degrades readability of stamped text.", "photo_status": "HARD"}	{"fields": {"make": {"value": "KPT Corporation", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "KOREA", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "Not present on nameplate", "quality": "Verify"}, "tag_number": {"value": "73-BV-0023", "quality": "Confirmed"}, "description": {"value": "VALVE,BALL", "quality": "Confirmed"}, "size_dimension": {"value": "2INCH 150#", "quality": "Verify"}, "year_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "month_of_manufacture": {"value": "Not present on nameplate", "quality": "Verify"}, "additional_information": {"value": "BODY/BONNET: MATERIAL - WCB", "quality": "Verify"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Nameplate is severely corroded, rusted, and heavily weathered. Most stamped data fields including serial number, model, and date of manufacture are illegible.", "qc_comment": "Heavy surface corrosion severely degrades readability of stamped text.", "photo_status": "HARD"}	/data/storage/exports/73-BV-0023/AI Output-73-BV-0023-VALVE,BALL.xlsx	/data/storage/exports/73-BV-0023/73-BV-0023-VALVE,BALL-Template.xlsx	2	2	2	2026-08-17 10:43:43.87506+00	2026-08-17 11:07:14.616661+00
58	12-M2-GV-0011	GATE VALVE	{"fields": {"make": {"value": "FB VALVE (www.fbvalve.com)", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "FV2408220017", "quality": "Confirmed"}, "tag_number": {"value": "12-M2-GV-0011", "quality": "Confirmed"}, "description": {"value": "GATE VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 6, CLASS 900", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "12", "quality": "Confirmed"}, "additional_information": {"value": "STANDARD: API 600, STANDARD: ASME B16.34, STANDARD: API 624, BODY: WCB, WEDGE: WCB+STL6, SEAT: A105N+STL6, STEM: 316/316L, OP.TEMP: 16.9 MPa @ 38°C, F TO F: 610±1.5", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Tag number and description supplied from asset register match plate context (no conflicting tag printed on plate). Manufacturer name not explicitly printed—only website/logo 'FB VALVE' visible, so marked Verify. Model, part number, weight, country, and hazardous area classification are not printed on this nameplate.", "qc_comment": "Plate is clear and well-lit; all printed fields are legible. Missing fields (model, part no, weight, country, hazard class) appear genuinely absent from this nameplate design.", "photo_status": "EASY"}	{"fields": {"make": {"value": "FB VALVE (www.fbvalve.com)", "quality": "Verify"}, "model": {"value": "Not present on nameplate", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "Not present on nameplate", "quality": "Verify"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "FV2408220017", "quality": "Confirmed"}, "tag_number": {"value": "12-M2-GV-0011", "quality": "Confirmed"}, "description": {"value": "GATE VALVE", "quality": "Confirmed"}, "size_dimension": {"value": "NPS 6, CLASS 900", "quality": "Confirmed"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "12", "quality": "Confirmed"}, "additional_information": {"value": "STANDARD: API 600, STANDARD: ASME B16.34, STANDARD: API 624, BODY: WCB, WEDGE: WCB+STL6, SEAT: A105N+STL6, STEM: 316/316L, OP.TEMP: 16.9 MPa @ 38°C, F TO F: 610±1.5", "quality": "Confirmed"}, "hazardous_classification": {"value": "Not present on nameplate", "quality": "Verify"}}, "remarks": "Tag number and description supplied from asset register match plate context (no conflicting tag printed on plate). Manufacturer name not explicitly printed—only website/logo 'FB VALVE' visible, so marked Verify. Model, part number, weight, country, and hazardous area classification are not printed on this nameplate.", "qc_comment": "Plate is clear and well-lit; all printed fields are legible. Missing fields (model, part no, weight, country, hazard class) appear genuinely absent from this nameplate design.", "photo_status": "EASY"}	/data/storage/exports/12-M2-GV-0011/AI Output-12-M2-GV-0011-GATE VALVE.xlsx	/data/storage/exports/12-M2-GV-0011/12-M2-GV-0011-GATE VALVE-Template.xlsx	\N	2	1	2026-08-19 11:40:02.218356+00	2026-08-19 11:40:02.218356+00
75	16-LIT-357	TRANSMITTER,LEVEL,INDICATING,NCR	{"fields": {"make": {"value": "EMERSON ROSEMOUNT", "quality": "Confirmed"}, "model": {"value": "3408A1SHA5E17R6AASAAM6C2C4AWQ4Q5Q8Q15Q73Q76WR3", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "SWEDEN", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "24GORK0008917", "quality": "Confirmed"}, "tag_number": {"value": "16-LIT-357", "quality": "Confirmed"}, "description": {"value": "TRANSMITTER,LEVEL,INDICATING,NCR", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "09", "quality": "Confirmed"}, "additional_information": {"value": "LEVEL TRANSMITTER, CERTIFICATE HOLDER: ROSEMOUNT TANK RADAR AB; LAYOUTVÄGEN 1; 435 33 MÖLNLYCKE SWEDEN, HART: 4-20 mA, SUPPLY: 35 VDC 22.5mA, DEVICE REV: 1, PROTOCOL: 7, HV/SV: 1.0.0/1.0.0 (1.A0), FCC ID: K8C3408T, IC: 2827A-3408T, HVIN: 3408T1, FM APPROVED, CE 2460, WARNING: POTENTIAL ELECTROSTATIC HAZARD - SEE INSTRUCTIONS, DO NOT REMOVE COVER WHILE CIRCUITS ARE LIVE, INSTALL PER CONTROL DRAWING D7000006-397", "quality": "Confirmed"}, "hazardous_classification": {"value": "FM23ATEX0001X, FM23UKEX0001X, FLAMEPROOF, II 1/2 G Ex db IIC T6...T2 Ga/Gb, II 2 G Ex db IIC T6...T2 Gb, II 1/2 D Ex tb IIIC T200 85°C...T200 250°C Da/Db, II 2 D Ex tb IIIC T200 85°C...T200 250°C Db, (-55°C ≤ Ta ≤ +70°C), IP6X", "quality": "Confirmed"}}, "remarks": "Model number is very long and partially truncated at the edge of the plate across all photos; transcribed from the clearest available (photo 2/3) but some trailing characters may be cut off. MFG DATE printed as 24-09 (year-month format), recorded as year 2024, month 09. Tag number on plate matches asset register (16-LIT-357).", "qc_comment": "Nameplate is largely legible across three clear close-up photos; model string length and possible truncation at plate edge is the main item to verify.", "photo_status": "EASY"}	{"fields": {"make": {"value": "EMERSON ROSEMOUNT", "quality": "Confirmed"}, "model": {"value": "3408A1SHA5E17R6AASAAM6C2C4AWQ4Q5Q8Q15Q73Q76WR3", "quality": "Verify"}, "weight": {"value": "Not present on nameplate", "quality": "Verify"}, "country": {"value": "SWEDEN", "quality": "Confirmed"}, "part_no": {"value": "Not present on nameplate", "quality": "Verify"}, "serial_no": {"value": "24GORK0008917", "quality": "Confirmed"}, "tag_number": {"value": "16-LIT-357", "quality": "Confirmed"}, "description": {"value": "TRANSMITTER,LEVEL,INDICATING,NCR", "quality": "Confirmed"}, "size_dimension": {"value": "Not present on nameplate", "quality": "Verify"}, "year_of_manufacture": {"value": "2024", "quality": "Confirmed"}, "month_of_manufacture": {"value": "09", "quality": "Confirmed"}, "additional_information": {"value": "LEVEL TRANSMITTER, CERTIFICATE HOLDER: ROSEMOUNT TANK RADAR AB; LAYOUTVÄGEN 1; 435 33 MÖLNLYCKE SWEDEN, HART: 4-20 mA, SUPPLY: 35 VDC 22.5mA, DEVICE REV: 1, PROTOCOL: 7, HV/SV: 1.0.0/1.0.0 (1.A0), FCC ID: K8C3408T, IC: 2827A-3408T, HVIN: 3408T1, FM APPROVED, CE 2460, WARNING: POTENTIAL ELECTROSTATIC HAZARD - SEE INSTRUCTIONS, DO NOT REMOVE COVER WHILE CIRCUITS ARE LIVE, INSTALL PER CONTROL DRAWING D7000006-397", "quality": "Confirmed"}, "hazardous_classification": {"value": "FM23ATEX0001X, FM23UKEX0001X, FLAMEPROOF, II 1/2 G Ex db IIC T6...T2 Ga/Gb, II 2 G Ex db IIC T6...T2 Gb, II 1/2 D Ex tb IIIC T200 85°C...T200 250°C Da/Db, II 2 D Ex tb IIIC T200 85°C...T200 250°C Db, (-55°C ≤ Ta ≤ +70°C), IP6X", "quality": "Confirmed"}}, "remarks": "Model number is very long and partially truncated at the edge of the plate across all photos; transcribed from the clearest available (photo 2/3) but some trailing characters may be cut off. MFG DATE printed as 24-09 (year-month format), recorded as year 2024, month 09. Tag number on plate matches asset register (16-LIT-357).", "qc_comment": "Nameplate is largely legible across three clear close-up photos; model string length and possible truncation at plate edge is the main item to verify.", "photo_status": "EASY"}	/data/storage/exports/16-LIT-357/AI Output-16-LIT-357-TRANSMITTER,LEVEL,INDICATING,NCR.xlsx	/data/storage/exports/16-LIT-357/16-LIT-357-TRANSMITTER,LEVEL,INDICATING,NCR-Template.xlsx	\N	3	1	2026-08-20 11:41:31.711668+00	2026-08-20 11:41:31.711668+00
\.


--
-- Data for Name: batch_items; Type: TABLE DATA; Schema: public; Owner: visioncore
--

COPY public.batch_items (id, batch_id, asset_tag_id, tag_number, description, status, error_message, created_at, updated_at) FROM stdin;
113	69	44	22-GV-0553	VALVE,GATE	completed	\N	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:53.473552+00
126	78	30	12-4020-BV-0074	VALVE,BALL	duplicate	Tag already extracted	2026-08-19 10:52:10.484461+00	2026-08-19 10:52:10.484461+00
91	54	30	12-4020-BV-0074	BALL VALVE	completed	\N	2026-08-17 10:01:52.693624+00	2026-08-17 10:02:15.986022+00
127	79	50	12-4020-NLV-0007	NEEDLE VALVE	duplicate	Tag already extracted	2026-08-19 11:08:06.802404+00	2026-08-19 11:08:06.802404+00
114	69	45	22-LT-702	TRANSMITTER,LEVEL	completed	\N	2026-08-19 07:04:41.831303+00	2026-08-19 07:05:16.891304+00
145	92	64	20-DZT-006	TRANSMITTER,DENSITY	completed	\N	2026-08-19 12:10:13.626795+00	2026-08-19 12:10:31.647575+00
93	55	31	12-4020-CC-0032	CORROSION COUPON	completed	\N	2026-08-17 10:05:13.018397+00	2026-08-17 10:05:50.505095+00
94	56	32	74-FG-024	GAUGE,SIGHT GLASS	completed	\N	2026-08-17 10:38:15.386386+00	2026-08-17 10:40:57.038969+00
128	80	53	12-GDF-03-0103	FLAMMABLE GAS DETECTOR	completed	\N	2026-08-19 11:09:57.162819+00	2026-08-19 11:10:20.185873+00
95	56	33	54-038-P12	EXTINGUISHER,DRY POWDER	completed	\N	2026-08-17 10:38:15.386386+00	2026-08-17 10:41:51.6822+00
116	70	46	51-PT-701	TRANSMITTER,PRESSURE	completed	\N	2026-08-19 07:08:30.747465+00	2026-08-19 07:08:40.524077+00
96	56	34	71-FV-003	VALVE,CONTROL,FLOW	completed	\N	2026-08-17 10:38:15.386386+00	2026-08-17 10:42:03.582937+00
138	88	60	12-M2-PI-0002	PRESSURE GAUGE	completed	\N	2026-08-19 11:42:53.203688+00	2026-08-19 11:43:10.614097+00
97	56	35	72-SSC-7203	SAMPLE COOLER	completed	\N	2026-08-17 10:38:15.386386+00	2026-08-17 10:42:27.358846+00
117	71	47	12-M2-PIT-0008	ELECTRONIC PRESSURE TRANSMITTER	completed	\N	2026-08-19 07:20:53.549498+00	2026-08-19 07:21:22.055696+00
118	72	41	21-JDD-01	JUNCTION BOX,INSTRUMENT	duplicate	Tag already extracted	2026-08-19 07:22:36.46058+00	2026-08-19 07:22:36.46058+00
98	56	36	73-BV-0023	VALVE,BALL	completed	\N	2026-08-17 10:38:15.386386+00	2026-08-17 10:43:43.87506+00
139	89	49	12-4020-FDI-21-0003	INFRARED FLAME DETECTOR	duplicate	Tag already extracted	2026-08-19 11:47:03.015804+00	2026-08-19 11:47:03.015804+00
115	69	46	51-PT-701	TRANSMITTER,PRESSURE	duplicate	\N	2026-08-19 07:04:41.831303+00	2026-08-19 08:15:01.829845+00
99	57	37	12	IJBF-1067-FIRE AND GAS JUNCTION BOX	completed	\N	2026-08-17 10:57:38.274319+00	2026-08-17 10:59:02.35202+00
119	73	41	21-JDD-01	JUNCTION BOX,INSTRUMENT	duplicate	Tag already extracted	2026-08-19 08:24:31.575019+00	2026-08-19 08:24:31.575019+00
129	81	54	12-M2-DBV-0002	DOUBLE BLOCK AND BLEED VALVE	completed	\N	2026-08-19 11:15:23.201615+00	2026-08-19 11:15:45.845526+00
100	58	38	12-4020-DBV-0004	DOUBLE BLOCK AND BLEED VALVE	completed	\N	2026-08-18 04:56:30.807109+00	2026-08-18 04:56:44.374848+00
92	54	31	12-4020-CC-0032	CORROSION COUPON	duplicate	\N	2026-08-17 10:01:52.693624+00	2026-08-19 09:04:17.815877+00
101	59	39	12-4021-TE-1001	TEMPERATURE ELEMENT	completed	\N	2026-08-18 05:05:39.697362+00	2026-08-18 05:05:56.774816+00
102	60	37	12	LJBF-1067-FIRE AND GAS JUNCTION BOX	duplicate	Tag already extracted	2026-08-18 05:18:45.395007+00	2026-08-18 05:18:45.395007+00
103	61	32	74-FG-024	GAUGE,SIGHT GLASS	duplicate	Tag already extracted	2026-08-18 05:19:14.36289+00	2026-08-18 05:19:14.36289+00
141	89	52	12-4020-BV-0083	BALL VALVE	duplicate	Tag already extracted	2026-08-19 11:47:03.015804+00	2026-08-19 11:47:03.015804+00
104	62	40	12-4020-FE-0031	FLOW ELEMENT	completed	\N	2026-08-18 06:08:25.333487+00	2026-08-18 06:08:35.264838+00
120	74	48	12-4020-BV	0073,BALL VALVE	completed	\N	2026-08-19 09:23:15.477229+00	2026-08-19 09:23:49.464594+00
105	63	41	21-JDD-01	JUNCTION BOX,INSTRUMENT	completed	\N	2026-08-18 06:26:13.236281+00	2026-08-18 06:26:23.586777+00
106	64	39	12-4021-TE-1001	TEMPERATURE ELEMENT	duplicate	Tag already extracted	2026-08-18 08:29:49.800829+00	2026-08-18 08:29:49.800829+00
130	81	55	12-M2-GV-0038	GATE VALVE	completed	\N	2026-08-19 11:15:23.201615+00	2026-08-19 11:15:56.892006+00
107	65	42	22-GV-0550	VALVE,GATE	completed	\N	2026-08-18 09:01:35.152388+00	2026-08-18 09:01:47.170947+00
108	66	41	21-JDD-01	JUNCTION BOX,INSTRUMENT	duplicate	Tag already extracted	2026-08-18 11:00:30.65151+00	2026-08-18 11:00:30.65151+00
121	75	49	12-4020-FDI-21-0003	INFRARED FLAME DETECTOR	completed	\N	2026-08-19 09:35:42.715478+00	2026-08-19 09:36:11.163132+00
109	67	43	12-ECP-0002	ELECTRIC CONTROL PANEL	completed	\N	2026-08-19 05:42:46.21322+00	2026-08-19 05:43:01.841406+00
110	68	30	12-4020-BV-0074	BALL VALVE	duplicate	Tag already extracted	2026-08-19 05:46:05.656309+00	2026-08-19 05:46:05.656309+00
111	69	41	21-JDD-01	JUNCTION BOX,INSTRUMENT	duplicate	Tag already extracted	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:41.831303+00
112	69	42	22-GV-0550	VALVE,GATE	duplicate	Tag already extracted	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:41.831303+00
151	95	73	2196JAM-CSS	PUSH BUTTON STATION	completed	\N	2026-08-20 11:29:26.751146+00	2026-08-20 11:29:55.052797+00
131	82	56	12-M2-PIT-0001	PRESSURE TRANSMITTER	completed	\N	2026-08-19 11:36:05.662009+00	2026-08-19 11:36:28.331076+00
122	75	50	12-4020-NLV-0007	NEEDLE VALVE	completed	\N	2026-08-19 09:35:42.715478+00	2026-08-19 09:36:34.540015+00
132	83	41	21-JDD-01	JUNCTION BOX,INSTRUMENT	duplicate	Tag already extracted	2026-08-19 11:39:08.952351+00	2026-08-19 11:39:08.952351+00
123	76	51	12-4020-BV-0073	BALL VALVE	completed	\N	2026-08-19 09:42:24.863356+00	2026-08-19 09:42:35.554396+00
140	89	61	12-4020-BV-0111	BALL VALVE	completed	\N	2026-08-19 11:47:03.015804+00	2026-08-19 11:47:14.283894+00
142	90	50	12-4020-NLV-0007	NEEDLE VALVE	duplicate	Tag already extracted	2026-08-19 11:53:47.909541+00	2026-08-19 11:53:47.909541+00
124	76	52	12-4020-BV-0083	BALL VALVE	completed	\N	2026-08-19 09:42:24.863356+00	2026-08-19 09:42:51.920968+00
125	77	30	12-4020-BV-0074	BALL VALVE	duplicate	Tag already extracted	2026-08-19 10:51:47.540984+00	2026-08-19 10:51:47.540984+00
133	83	57	12-M2-PIT	0008 ELECTRONIC PRESSURE TRANSMITTER	completed	\N	2026-08-19 11:39:08.952351+00	2026-08-19 11:39:29.029762+00
134	84	58	12-M2-GV-0011	GATE VALVE	completed	\N	2026-08-19 11:39:50.079227+00	2026-08-19 11:40:02.218356+00
148	94	70	16-NRV-1268	VALVE,CHECK,3INX300LBS	completed	\N	2026-08-20 11:27:28.054792+00	2026-08-20 11:27:45.354817+00
146	93	68	35-SFX-015	FIRE EXTINGUISHER,DCP,9KG	completed	\N	2026-08-20 11:25:53.082352+00	2026-08-20 11:26:05.313752+00
135	85	59	22-LT	702 TRANSMITTER,LEVEL	completed	\N	2026-08-19 11:40:50.249935+00	2026-08-19 11:41:01.561988+00
136	86	44	22-GV-0553	VALVE,GATE	duplicate	Tag already extracted	2026-08-19 11:42:02.663978+00	2026-08-19 11:42:02.663978+00
137	87	42	22-GV-0550	VALVE,GATE	duplicate	Tag already extracted	2026-08-19 11:42:17.667056+00	2026-08-19 11:42:17.667056+00
143	91	62	16-GV-1982	VALVE,GATE	completed	\N	2026-08-19 12:04:27.7187+00	2026-08-19 12:04:39.778652+00
154	97	76	72-LSL-102X	SWITCH,LEVEL	completed	\N	2026-08-20 11:42:06.473018+00	2026-08-20 11:42:32.484037+00
150	95	72	72-PSV-003B	VALVE,PRESSURE SAFETY,3-X 4IN,SP29.5BAR	completed	\N	2026-08-20 11:29:26.751146+00	2026-08-20 11:29:46.815028+00
144	91	63	PM	8981B MOTOR,PUMP	completed	\N	2026-08-19 12:04:27.7187+00	2026-08-19 12:05:08.597256+00
147	93	69	35-XL-01A-018	BEACON,FLASH,AMBER,24VDC	completed	\N	2026-08-20 11:25:53.082352+00	2026-08-20 11:26:32.986278+00
149	94	71	35-GDF-01A-007	DETECTOR,FLAMMABLE GAS,IR,0TO100%LEL	completed	\N	2026-08-20 11:27:28.054792+00	2026-08-20 11:27:59.750715+00
153	96	75	16-LIT-357	TRANSMITTER,LEVEL,INDICATING,NCR	completed	\N	2026-08-20 11:41:12.796729+00	2026-08-20 11:41:31.711668+00
152	95	74	73-PV-029	VALVE,CONTROL,PRESSURE2IN	completed	\N	2026-08-20 11:29:26.751146+00	2026-08-20 11:30:05.961083+00
155	97	77	73-TV-208X	VALVE,CONTROL,TEMPERATURE,3IN	completed	\N	2026-08-20 11:42:06.473018+00	2026-08-20 11:42:54.897116+00
\.


--
-- Data for Name: batches; Type: TABLE DATA; Schema: public; Owner: visioncore
--

COPY public.batches (id, reference, user_id, status, total_images, total_tags, created_at, updated_at) FROM stdin;
90	B-20260819-965018	3	uploaded	2	1	2026-08-19 11:53:47.909541+00	2026-08-19 11:53:47.909541+00
55	B-20260817-CF6061	2	completed	1	1	2026-08-17 10:05:13.018397+00	2026-08-17 10:05:50.522345+00
91	B-20260819-189961	2	completed	2	2	2026-08-19 12:04:27.7187+00	2026-08-19 12:05:08.616308+00
56	B-20260817-8DFACD	2	completed	5	5	2026-08-17 10:38:15.386386+00	2026-08-17 10:43:43.896519+00
57	B-20260817-F4239C	2	completed	1	1	2026-08-17 10:57:38.274319+00	2026-08-17 10:59:02.369056+00
58	B-20260818-F3DBC6	2	completed	1	1	2026-08-18 04:56:30.807109+00	2026-08-18 04:56:44.39828+00
92	B-20260819-4E7420	2	completed	2	1	2026-08-19 12:10:13.626795+00	2026-08-19 12:10:31.66965+00
59	B-20260818-B77D4B	2	completed	1	1	2026-08-18 05:05:39.697362+00	2026-08-18 05:05:56.792564+00
60	B-20260818-78D1B5	2	uploaded	1	1	2026-08-18 05:18:45.395007+00	2026-08-18 05:18:45.395007+00
61	B-20260818-B19BB0	2	uploaded	1	1	2026-08-18 05:19:14.36289+00	2026-08-18 05:19:14.36289+00
62	B-20260818-B86933	2	completed	1	1	2026-08-18 06:08:25.333487+00	2026-08-18 06:08:35.283074+00
63	B-20260818-543192	2	completed	1	1	2026-08-18 06:26:13.236281+00	2026-08-18 06:26:23.605693+00
64	B-20260818-A4D829	2	uploaded	1	1	2026-08-18 08:29:49.800829+00	2026-08-18 08:29:49.800829+00
93	B-20260820-18853E	3	completed	5	2	2026-08-20 11:25:53.082352+00	2026-08-20 11:26:33.00651+00
65	B-20260818-042EA2	2	completed	1	1	2026-08-18 09:01:35.152388+00	2026-08-18 09:01:47.189916+00
66	B-20260818-9813C8	4	uploaded	1	1	2026-08-18 11:00:30.65151+00	2026-08-18 11:00:30.65151+00
67	B-20260819-59EEA7	1	completed	1	1	2026-08-19 05:42:46.21322+00	2026-08-19 05:43:01.860256+00
68	B-20260819-C7BDE0	1	uploaded	1	1	2026-08-19 05:46:05.656309+00	2026-08-19 05:46:05.656309+00
94	B-20260820-02C1F9	3	completed	3	2	2026-08-20 11:27:28.054792+00	2026-08-20 11:27:59.767686+00
70	B-20260819-06E6C0	2	completed	1	1	2026-08-19 07:08:30.747465+00	2026-08-19 07:08:40.539838+00
71	B-20260819-5295A7	2	completed	3	1	2026-08-19 07:20:53.549498+00	2026-08-19 07:21:22.072981+00
72	B-20260819-DB1B38	2	uploaded	3	1	2026-08-19 07:22:36.46058+00	2026-08-19 07:22:36.46058+00
95	B-20260820-D1B169	3	completed	3	3	2026-08-20 11:29:26.751146+00	2026-08-20 11:30:05.97849+00
69	B-20260819-10430B	2	completed	5	5	2026-08-19 07:04:41.831303+00	2026-08-19 08:15:01.844979+00
73	B-20260819-4B77DA	3	uploaded	1	1	2026-08-19 08:24:31.575019+00	2026-08-19 08:24:31.575019+00
54	B-20260817-263222	2	completed	2	2	2026-08-17 10:01:52.693624+00	2026-08-19 09:04:17.831082+00
74	B-20260819-64218E	3	completed	2	1	2026-08-19 09:23:15.477229+00	2026-08-19 09:23:49.481957+00
96	B-20260820-E14389	3	completed	3	1	2026-08-20 11:41:12.796729+00	2026-08-20 11:41:31.732237+00
75	B-20260819-8DD594	3	completed	3	2	2026-08-19 09:35:42.715478+00	2026-08-19 09:36:34.559866+00
76	B-20260819-80AECD	3	completed	2	2	2026-08-19 09:42:24.863356+00	2026-08-19 09:42:51.93583+00
77	B-20260819-15A5C5	2	uploaded	1	1	2026-08-19 10:51:47.540984+00	2026-08-19 10:51:47.540984+00
78	B-20260819-A86717	2	uploaded	1	1	2026-08-19 10:52:10.484461+00	2026-08-19 10:52:10.484461+00
79	B-20260819-187EC6	3	uploaded	2	1	2026-08-19 11:08:06.802404+00	2026-08-19 11:08:06.802404+00
80	B-20260819-E8FCE5	3	completed	2	1	2026-08-19 11:09:57.162819+00	2026-08-19 11:10:20.205948+00
97	B-20260820-747BD8	3	completed	2	2	2026-08-20 11:42:06.473018+00	2026-08-20 11:42:54.912862+00
81	B-20260819-5F5B24	3	completed	3	2	2026-08-19 11:15:23.201615+00	2026-08-19 11:15:56.908187+00
82	B-20260819-E833FC	3	completed	3	1	2026-08-19 11:36:05.662009+00	2026-08-19 11:36:28.345713+00
83	B-20260819-461A32	2	completed	2	2	2026-08-19 11:39:08.952351+00	2026-08-19 11:39:29.046739+00
84	B-20260819-62AA5C	2	completed	1	1	2026-08-19 11:39:50.079227+00	2026-08-19 11:40:02.244613+00
85	B-20260819-FD0A12	2	completed	1	1	2026-08-19 11:40:50.249935+00	2026-08-19 11:41:01.578184+00
86	B-20260819-0C73FE	2	uploaded	1	1	2026-08-19 11:42:02.663978+00	2026-08-19 11:42:02.663978+00
87	B-20260819-34F3BD	2	uploaded	1	1	2026-08-19 11:42:17.667056+00	2026-08-19 11:42:17.667056+00
88	B-20260819-F58C90	3	completed	3	1	2026-08-19 11:42:53.203688+00	2026-08-19 11:43:10.737504+00
89	B-20260819-C2C95B	3	completed	4	3	2026-08-19 11:47:03.015804+00	2026-08-19 11:47:14.298756+00
\.


--
-- Data for Name: org_credits; Type: TABLE DATA; Schema: public; Owner: visioncore
--

COPY public.org_credits (id, total_purchased_usd, updated_by_user_id, created_at, updated_at, ledger_usage_usd, ledger_through_date) FROM stdin;
1	20.01	1	2026-08-20 07:34:17.621648+00	2026-08-27 04:48:51.937381+00	1.1296	2026-08-26
\.


--
-- Data for Name: tag_images; Type: TABLE DATA; Schema: public; Owner: visioncore
--

COPY public.tag_images (id, item_id, original_filename, stored_path, media_type, size_bytes, created_at, updated_at, content_hash) FROM stdin;
97	91	12-4020-BV-0074-BALL VALVE.jpg	/data/storage/uploads/B-20260817-263222/12-4020-BV-0074/7913a5630aa342a8822c909f64572767.jpg	image/jpeg	2316480	2026-08-17 10:01:52.693624+00	2026-08-17 10:01:52.693624+00	4cb90a44b4a670df05a5e61e8dde9916a26cc05f38f45a7c8f95db30c7cff44b
98	92	12-4020-CC-0032-CORROSION COUPON.jpg	/data/storage/uploads/B-20260817-263222/12-4020-CC-0032/b1d745849d454001ab87961e93af7f05.jpg	image/jpeg	2010134	2026-08-17 10:01:52.693624+00	2026-08-17 10:01:52.693624+00	b8ffe0ba8a0f7bd4defecf2e5fc02cb3627a6010c64da1af12a357e683f7fe26
99	93	12-4020-CC-0032-CORROSION COUPON.jpg	/data/storage/uploads/B-20260817-263222/12-4020-CC-0032/b1d745849d454001ab87961e93af7f05.jpg	image/jpeg	2010134	2026-08-17 10:05:13.018397+00	2026-08-17 10:05:13.018397+00	b8ffe0ba8a0f7bd4defecf2e5fc02cb3627a6010c64da1af12a357e683f7fe26
100	94	74-FG-024-GAUGE,SIGHT GLASS.jpg	/data/storage/uploads/B-20260817-8DFACD/74-FG-024/d82b4cd727bb424d8fa5a2244346fd14.jpg	image/jpeg	509571	2026-08-17 10:38:15.386386+00	2026-08-17 10:38:15.386386+00	4559c9dfbea5daaf3199eeb05e259af831d3414db0390fa6726300ede762f5a3
101	95	54-038-P12-EXTINGUISHER,DRY POWDER.jpg	/data/storage/uploads/B-20260817-8DFACD/54-038-P12/a9118f210a7d41fd852a825e1c684d8a.jpg	image/jpeg	320843	2026-08-17 10:38:15.386386+00	2026-08-17 10:38:15.386386+00	652dc7da3796695b81f5c9645612424a6b5927d0e380e640b8c2ab41a314867c
102	96	71-FV-003-VALVE,CONTROL,FLOW.jpg	/data/storage/uploads/B-20260817-8DFACD/71-FV-003/5bd7eec44fd94cb28459325fd252079c.jpg	image/jpeg	4732996	2026-08-17 10:38:15.386386+00	2026-08-17 10:38:15.386386+00	cba5210c57db1f48e6c426bc734b066bc14d66c36ef309ef1c8b7ec01f6251e1
103	97	72-SSC-7203-SAMPLE COOLER.jpg	/data/storage/uploads/B-20260817-8DFACD/72-SSC-7203/94779dde8fbc4cc5876ffce2ca633565.jpg	image/jpeg	1653854	2026-08-17 10:38:15.386386+00	2026-08-17 10:38:15.386386+00	85d87fa695b5aea8898ed61df33f6b5714418f028a3a736cd4912bbf980099f6
104	98	73-BV-0023-VALVE,BALL.jpg	/data/storage/uploads/B-20260817-8DFACD/73-BV-0023/3fe6366e229a4e268dc2d741b467a99e.jpg	image/jpeg	1458218	2026-08-17 10:38:15.386386+00	2026-08-17 10:38:15.386386+00	cfaea42b048dfb32976f4b2ff145d339fd7247e796897b871fbbce9dc56081e3
105	99	12-IJBF-1067-FIRE AND GAS JUNCTION BOX.jpg	/data/storage/uploads/B-20260817-F4239C/12/28e0a4cdbe4c4595a66ed19058fa33b6.jpg	image/jpeg	2300375	2026-08-17 10:57:38.274319+00	2026-08-17 10:57:38.274319+00	13285bb26c2e8a1fe0b16ebf783d65b94258b8aab99eb5c4bb21c383d893d098
106	100	12-4020-DBV-0004-DOUBLE BLOCK AND BLEED VALVE.png	/data/storage/uploads/B-20260818-F3DBC6/12-4020-DBV-0004/526f49b4e4724856b8b300358bb318de.png	image/png	3872580	2026-08-18 04:56:30.807109+00	2026-08-18 04:56:30.807109+00	e046e54b7e205f6b58d40c68f59fb2bb89883d0095b327cfacf93bd8f64f8785
107	101	12-4021-TE-1001-TEMPERATURE ELEMENT.jpg	/data/storage/uploads/B-20260818-B77D4B/12-4021-TE-1001/0d87248510c24abfb3ec99ace2ccf8c7.jpg	image/jpeg	5152130	2026-08-18 05:05:39.697362+00	2026-08-18 05:05:39.697362+00	5cb624c71a57faba3d446fd2bd10331d715d8aafeddcb6f61065d5f3312a6fa1
108	102	12-lJBF-1067-FIRE AND GAS JUNCTION BOX.jpg	/data/storage/uploads/B-20260817-F4239C/12/28e0a4cdbe4c4595a66ed19058fa33b6.jpg	image/jpeg	2300375	2026-08-18 05:18:45.395007+00	2026-08-18 05:18:45.395007+00	13285bb26c2e8a1fe0b16ebf783d65b94258b8aab99eb5c4bb21c383d893d098
109	103	74-FG-024-GAUGE,SIGHT GLASS.jpg	/data/storage/uploads/B-20260817-8DFACD/74-FG-024/d82b4cd727bb424d8fa5a2244346fd14.jpg	image/jpeg	509571	2026-08-18 05:19:14.36289+00	2026-08-18 05:19:14.36289+00	4559c9dfbea5daaf3199eeb05e259af831d3414db0390fa6726300ede762f5a3
110	104	12-4020-FE-0031-FLOW ELEMENT.jpg	/data/storage/uploads/B-20260818-B86933/12-4020-FE-0031/d7d50d0e3a5043fa9dec3697c3a705ae.jpg	image/jpeg	2206839	2026-08-18 06:08:25.333487+00	2026-08-18 06:08:25.333487+00	9b48d8b35685f9746c22260d0bf96996ff95d51c4fea40942b50069248469d74
111	105	21-JDD-01-JUNCTION BOX,INSTRUMENT.jpg	/data/storage/uploads/B-20260818-543192/21-JDD-01/2a7274a1f6b9433088fe1d872ede9132.jpg	image/jpeg	4666333	2026-08-18 06:26:13.236281+00	2026-08-18 06:26:13.236281+00	2a339f30fc5da655a570959e44b0c724f69912f6dba3182e68453323f592ab4d
112	106	12-4021-TE-1001-TEMPERATURE ELEMENT.jpg	/data/storage/uploads/B-20260818-B77D4B/12-4021-TE-1001/0d87248510c24abfb3ec99ace2ccf8c7.jpg	image/jpeg	5152130	2026-08-18 08:29:49.800829+00	2026-08-18 08:29:49.800829+00	5cb624c71a57faba3d446fd2bd10331d715d8aafeddcb6f61065d5f3312a6fa1
113	107	22-GV-0550-VALVE,GATE.jpg	/data/storage/uploads/B-20260818-042EA2/22-GV-0550/6ec0e95584b141428a07cd33d8dec780.jpg	image/jpeg	2026128	2026-08-18 09:01:35.152388+00	2026-08-18 09:01:35.152388+00	c3d4a52ed66986dd350256095890d55ed1e0e760d46e9cd47df00bfaef7c6528
114	108	21-JDD-01-JUNCTION BOX,INSTRUMENT.jpg	/data/storage/uploads/B-20260818-543192/21-JDD-01/2a7274a1f6b9433088fe1d872ede9132.jpg	image/jpeg	4666333	2026-08-18 11:00:30.65151+00	2026-08-18 11:00:30.65151+00	2a339f30fc5da655a570959e44b0c724f69912f6dba3182e68453323f592ab4d
115	109	12-ECP-0002-ELECTRIC CONTROL PANEL.jpg	/data/storage/uploads/B-20260819-59EEA7/12-ECP-0002/92d913f710c14e13acd04b07c8bf59e0.jpg	image/jpeg	2441130	2026-08-19 05:42:46.21322+00	2026-08-19 05:42:46.21322+00	0a807d021aad0402f5dc7db0038fbec23abc282b96ecb31898aaac0511dfc092
116	110	12-4020-BV-0074-BALL VALVE.jpg	/data/storage/uploads/B-20260817-263222/12-4020-BV-0074/7913a5630aa342a8822c909f64572767.jpg	image/jpeg	2316480	2026-08-19 05:46:05.656309+00	2026-08-19 05:46:05.656309+00	4cb90a44b4a670df05a5e61e8dde9916a26cc05f38f45a7c8f95db30c7cff44b
117	111	21-JDD-01-JUNCTION BOX,INSTRUMENT.jpg	/data/storage/uploads/B-20260818-543192/21-JDD-01/2a7274a1f6b9433088fe1d872ede9132.jpg	image/jpeg	4666333	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:41.831303+00	2a339f30fc5da655a570959e44b0c724f69912f6dba3182e68453323f592ab4d
118	112	22-GV-0550-VALVE,GATE.jpg	/data/storage/uploads/B-20260818-042EA2/22-GV-0550/6ec0e95584b141428a07cd33d8dec780.jpg	image/jpeg	2026128	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:41.831303+00	c3d4a52ed66986dd350256095890d55ed1e0e760d46e9cd47df00bfaef7c6528
119	113	22-GV-0553-VALVE,GATE.jpg	/data/storage/uploads/B-20260819-10430B/22-GV-0553/54bd04c6215d46f28ffba197cbd6c056.jpg	image/jpeg	5765033	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:41.831303+00	06d92328df27924834f1ff45ed9bbe39a0105b78c6a6243141ab596742aa0633
120	114	22-LT-702-TRANSMITTER,LEVEL.jpg	/data/storage/uploads/B-20260819-10430B/22-LT-702/2eb98922704c4f6f83f9a49e189dcfa3.jpg	image/jpeg	4937149	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:41.831303+00	7cd1ffbf7b648daffd168d2b139703472f4b70f8cef0869548554a4beadbff84
121	115	51-PT-701-TRANSMITTER,PRESSURE.jpg	/data/storage/uploads/B-20260819-10430B/51-PT-701/3414b35aa02b44b3a548ce2da1c353c5.jpg	image/jpeg	223420	2026-08-19 07:04:41.831303+00	2026-08-19 07:04:41.831303+00	6b4788feb94530a5b3bb13ecdca630ad8e649e7c0dc0405349439731401f192e
122	116	51-PT-701-TRANSMITTER,PRESSURE.jpg	/data/storage/uploads/B-20260819-10430B/51-PT-701/3414b35aa02b44b3a548ce2da1c353c5.jpg	image/jpeg	223420	2026-08-19 07:08:30.747465+00	2026-08-19 07:08:30.747465+00	6b4788feb94530a5b3bb13ecdca630ad8e649e7c0dc0405349439731401f192e
123	117	12-M2-PIT-0008-ELECTRONIC PRESSURE TRANSMITTER-1.jpg	/data/storage/uploads/B-20260818-543192/21-JDD-01/2a7274a1f6b9433088fe1d872ede9132.jpg	image/jpeg	4666333	2026-08-19 07:20:53.549498+00	2026-08-19 07:20:53.549498+00	2a339f30fc5da655a570959e44b0c724f69912f6dba3182e68453323f592ab4d
124	117	12-M2-PIT-0008-ELECTRONIC PRESSURE TRANSMITTER-2.jpg	/data/storage/uploads/B-20260818-042EA2/22-GV-0550/6ec0e95584b141428a07cd33d8dec780.jpg	image/jpeg	2026128	2026-08-19 07:20:53.549498+00	2026-08-19 07:20:53.549498+00	c3d4a52ed66986dd350256095890d55ed1e0e760d46e9cd47df00bfaef7c6528
125	117	12-M2-PIT-0008-ELECTRONIC PRESSURE TRANSMITTER.png	/data/storage/uploads/B-20260819-5295A7/12-M2-PIT-0008/2e95790d124b4c67b90a191f1676aa25.png	image/png	4269994	2026-08-19 07:20:53.549498+00	2026-08-19 07:20:53.549498+00	96bd35eea85569930c19acb17015289bb6edbe486b44c63fc5fbc215b158d81b
126	118	12-M2-PIT-0008-ELECTRONIC PRESSURE TRANSMITTER.png	/data/storage/uploads/B-20260819-5295A7/12-M2-PIT-0008/2e95790d124b4c67b90a191f1676aa25.png	image/png	4269994	2026-08-19 07:22:36.46058+00	2026-08-19 07:22:36.46058+00	96bd35eea85569930c19acb17015289bb6edbe486b44c63fc5fbc215b158d81b
127	118	21-JDD-01-JUNCTION BOX,INSTRUMENT.jpg	/data/storage/uploads/B-20260818-543192/21-JDD-01/2a7274a1f6b9433088fe1d872ede9132.jpg	image/jpeg	4666333	2026-08-19 07:22:36.46058+00	2026-08-19 07:22:36.46058+00	2a339f30fc5da655a570959e44b0c724f69912f6dba3182e68453323f592ab4d
128	118	22-GV-0550-VALVE,GATE.jpg	/data/storage/uploads/B-20260818-042EA2/22-GV-0550/6ec0e95584b141428a07cd33d8dec780.jpg	image/jpeg	2026128	2026-08-19 07:22:36.46058+00	2026-08-19 07:22:36.46058+00	c3d4a52ed66986dd350256095890d55ed1e0e760d46e9cd47df00bfaef7c6528
129	119	21-JDD-01-JUNCTION BOX,INSTRUMENT.jpg	/data/storage/uploads/B-20260818-543192/21-JDD-01/2a7274a1f6b9433088fe1d872ede9132.jpg	image/jpeg	4666333	2026-08-19 08:24:31.575019+00	2026-08-19 08:24:31.575019+00	2a339f30fc5da655a570959e44b0c724f69912f6dba3182e68453323f592ab4d
130	120	12-4020-BV-0073,BALL VALVE.jpg	/data/storage/uploads/B-20260819-64218E/12-4020-BV/a9b82be8008c4b108dfbf38a92bbde84.jpg	image/jpeg	4864574	2026-08-19 09:23:15.477229+00	2026-08-19 09:23:15.477229+00	d580a0e171a42850b6d4309771eed841044025e75e997e6f5b66b6884c278b51
131	120	12-4020-BV-0083,BALL VALVE.jpg	/data/storage/uploads/B-20260819-64218E/12-4020-BV/98603df592bf49888437852370ba7bf6.jpg	image/jpeg	2109494	2026-08-19 09:23:15.477229+00	2026-08-19 09:23:15.477229+00	a851eaa7e2133cca22b99fc12d4d40b9cf068ff80206eea95aa47bdc966b4e1e
132	121	12-4020-FDI-21-0003-INFRARED FLAME DETECTOR.jpg	/data/storage/uploads/B-20260819-8DD594/12-4020-FDI-21-0003/d69573081aa143ffa19d5f84aaf9af1f.jpg	image/jpeg	1445292	2026-08-19 09:35:42.715478+00	2026-08-19 09:35:42.715478+00	d0e8c195927ff2d07cfa4536e49e5603310df5c3eb641f38e22eb255f224085a
133	122	12-4020-NLV-0007-NEEDLE VALVE(1).jpg	/data/storage/uploads/B-20260819-8DD594/12-4020-NLV-0007/15fbe0007504487393d44483be0cfcfb.jpg	image/jpeg	5257996	2026-08-19 09:35:42.715478+00	2026-08-19 09:35:42.715478+00	53589e2997ab607cb5b4f681d0848cab7a8d97d12cc6499c9bda1ac63fe502ab
134	122	12-4020-NLV-0007-NEEDLE VALVE(2).jpg	/data/storage/uploads/B-20260819-8DD594/12-4020-NLV-0007/e363ff1f0d964ceebabea7441977742d.jpg	image/jpeg	5269722	2026-08-19 09:35:42.715478+00	2026-08-19 09:35:42.715478+00	00d7e067118222298850e4fb7f3ba7b94759e2268708047f76e6930e670bb2a2
135	123	12-4020-BV-0073-BALL VALVE.jpg	/data/storage/uploads/B-20260819-64218E/12-4020-BV/a9b82be8008c4b108dfbf38a92bbde84.jpg	image/jpeg	4864574	2026-08-19 09:42:24.863356+00	2026-08-19 09:42:24.863356+00	d580a0e171a42850b6d4309771eed841044025e75e997e6f5b66b6884c278b51
136	124	12-4020-BV-0083-BALL VALVE.jpg	/data/storage/uploads/B-20260819-64218E/12-4020-BV/98603df592bf49888437852370ba7bf6.jpg	image/jpeg	2109494	2026-08-19 09:42:24.863356+00	2026-08-19 09:42:24.863356+00	a851eaa7e2133cca22b99fc12d4d40b9cf068ff80206eea95aa47bdc966b4e1e
137	125	12-4020-BV-0074-BALL VALVE.jpg	/data/storage/uploads/B-20260817-263222/12-4020-BV-0074/7913a5630aa342a8822c909f64572767.jpg	image/jpeg	2316480	2026-08-19 10:51:47.540984+00	2026-08-19 10:51:47.540984+00	4cb90a44b4a670df05a5e61e8dde9916a26cc05f38f45a7c8f95db30c7cff44b
138	126	12-4020-BV-0074-VALVE,BALL.jpg	/data/storage/uploads/B-20260817-263222/12-4020-BV-0074/7913a5630aa342a8822c909f64572767.jpg	image/jpeg	2316480	2026-08-19 10:52:10.484461+00	2026-08-19 10:52:10.484461+00	4cb90a44b4a670df05a5e61e8dde9916a26cc05f38f45a7c8f95db30c7cff44b
139	127	12-4020-NLV-0007-NEEDLE VALVE(1).jpg	/data/storage/uploads/B-20260819-8DD594/12-4020-NLV-0007/15fbe0007504487393d44483be0cfcfb.jpg	image/jpeg	5257996	2026-08-19 11:08:06.802404+00	2026-08-19 11:08:06.802404+00	53589e2997ab607cb5b4f681d0848cab7a8d97d12cc6499c9bda1ac63fe502ab
140	127	12-4020-NLV-0007-NEEDLE VALVE(2).jpg	/data/storage/uploads/B-20260819-8DD594/12-4020-NLV-0007/e363ff1f0d964ceebabea7441977742d.jpg	image/jpeg	5269722	2026-08-19 11:08:06.802404+00	2026-08-19 11:08:06.802404+00	00d7e067118222298850e4fb7f3ba7b94759e2268708047f76e6930e670bb2a2
141	128	12-GDF-03-0103-FLAMMABLE GAS DETECTOR(1).jpg	/data/storage/uploads/B-20260819-E8FCE5/12-GDF-03-0103/c0c3ee69834d4cd6a75c3f56958bd8c0.jpg	image/jpeg	2111462	2026-08-19 11:09:57.162819+00	2026-08-19 11:09:57.162819+00	4c9a7a3ac0f8b7d904a39cc415e0201fef157ea28c6865f6f46ea552732c0bea
142	128	12-GDF-03-0103-FLAMMABLE GAS DETECTOR(2).jpg	/data/storage/uploads/B-20260819-E8FCE5/12-GDF-03-0103/5f0c93545a87404ab63ca594fd1af30c.jpg	image/jpeg	5221051	2026-08-19 11:09:57.162819+00	2026-08-19 11:09:57.162819+00	339f67c10904670ebd97b150a8507d8afceeec4b409b80208742f3526f9b7790
143	129	12-M2-DBV-0002-DOUBLE BLOCK AND BLEED VALVE(1).jpg	/data/storage/uploads/B-20260819-5F5B24/12-M2-DBV-0002/9ed6caaf088e41148736f964c795c1f4.jpg	image/jpeg	4633890	2026-08-19 11:15:23.201615+00	2026-08-19 11:15:23.201615+00	fcccc5de8e484c906af0e31c693712b01e7d432dae14ac15170c2d7b88d17557
144	129	12-M2-DBV-0002-DOUBLE BLOCK AND BLEED VALVE(2).jpg	/data/storage/uploads/B-20260819-5F5B24/12-M2-DBV-0002/69f417d257a44d958f0d0095f6623a83.jpg	image/jpeg	1799370	2026-08-19 11:15:23.201615+00	2026-08-19 11:15:23.201615+00	1da080d5052b5bd1ae50984ed09106a8e58ff683a5eca4b153d301564300f07c
145	130	12-M2-GV-0038-GATE VALVE.jpg	/data/storage/uploads/B-20260819-5F5B24/12-M2-GV-0038/fa082f64d49a40fb83120f641c706034.jpg	image/jpeg	2054015	2026-08-19 11:15:23.201615+00	2026-08-19 11:15:23.201615+00	e9b82ed146cf6deef1803f7d84997598056ea5804494fdc0b4fa15f154d7f982
146	131	12-M2-PIT-0001-PRESSURE TRANSMITTER(2).jpg	/data/storage/uploads/B-20260819-E833FC/12-M2-PIT-0001/c8f93b6a68274c1185cbb4275b4d130a.jpg	image/jpeg	2390763	2026-08-19 11:36:05.662009+00	2026-08-19 11:36:05.662009+00	dc79d43da38d078b87bffc62be6c3a6bb2805bd39fcb25c12d3a5226980020d8
147	131	12-M2-PIT-0001-PRESSURE TRANSMITTER(3).jpg	/data/storage/uploads/B-20260819-E833FC/12-M2-PIT-0001/6130781646d5424c97a48b7387f5d8cb.jpg	image/jpeg	2107334	2026-08-19 11:36:05.662009+00	2026-08-19 11:36:05.662009+00	052d59a7fc2adeb1a888ded913d6dddfb3169f7a30e0624a857e3d4ec5142f24
148	131	12-M2-PIT-0001-PRESSURE TRANSMITTER(1).jpg	/data/storage/uploads/B-20260819-E833FC/12-M2-PIT-0001/cbe5a2a5fef849ff95c12b23e47b336b.jpg	image/jpeg	5202748	2026-08-19 11:36:05.662009+00	2026-08-19 11:36:05.662009+00	c681a186b352a25fe049ead56e74292b08ed5870196b409155cf732cdb69dc3b
149	132	21-JDD-01,JUNCTION BOX,INSTRUMENT.jpg	/data/storage/uploads/B-20260818-543192/21-JDD-01/2a7274a1f6b9433088fe1d872ede9132.jpg	image/jpeg	4666333	2026-08-19 11:39:08.952351+00	2026-08-19 11:39:08.952351+00	2a339f30fc5da655a570959e44b0c724f69912f6dba3182e68453323f592ab4d
150	133	12-M2-PIT-0008 ELECTRONIC PRESSURE TRANSMITTER.png	/data/storage/uploads/B-20260819-5295A7/12-M2-PIT-0008/2e95790d124b4c67b90a191f1676aa25.png	image/png	4269994	2026-08-19 11:39:08.952351+00	2026-08-19 11:39:08.952351+00	96bd35eea85569930c19acb17015289bb6edbe486b44c63fc5fbc215b158d81b
151	134	12-M2-GV-0011,GATE VALVE.jpg	/data/storage/uploads/B-20260819-62AA5C/12-M2-GV-0011/8aa88e481e7b4e7fb0f78f57d89e7c70.jpg	image/jpeg	5269497	2026-08-19 11:39:50.079227+00	2026-08-19 11:39:50.079227+00	a21e5cdf0fdfb090bc36d39b3d207f36cd925ab3e90a69832fce809ddfa5b3e1
152	135	22-LT-702 TRANSMITTER,LEVEL.jpg	/data/storage/uploads/B-20260819-10430B/22-LT-702/2eb98922704c4f6f83f9a49e189dcfa3.jpg	image/jpeg	4937149	2026-08-19 11:40:50.249935+00	2026-08-19 11:40:50.249935+00	7cd1ffbf7b648daffd168d2b139703472f4b70f8cef0869548554a4beadbff84
153	136	22-GV-0553_VALVE,GATE.jpg	/data/storage/uploads/B-20260819-10430B/22-GV-0553/54bd04c6215d46f28ffba197cbd6c056.jpg	image/jpeg	5765033	2026-08-19 11:42:02.663978+00	2026-08-19 11:42:02.663978+00	06d92328df27924834f1ff45ed9bbe39a0105b78c6a6243141ab596742aa0633
154	137	22-GV-0550_VALVE,GATE.jpg	/data/storage/uploads/B-20260818-042EA2/22-GV-0550/6ec0e95584b141428a07cd33d8dec780.jpg	image/jpeg	2026128	2026-08-19 11:42:17.667056+00	2026-08-19 11:42:17.667056+00	c3d4a52ed66986dd350256095890d55ed1e0e760d46e9cd47df00bfaef7c6528
155	138	12-M2-PI-0002-PRESSURE GAUGE(2).jpg	/data/storage/uploads/B-20260819-F58C90/12-M2-PI-0002/d9220908e287434a878656f8af03e1d5.jpg	image/jpeg	2556295	2026-08-19 11:42:53.203688+00	2026-08-19 11:42:53.203688+00	f8dfef673c062534dc225220bf5cb4e7436f083d8efda8050c4edd1de1f23d30
156	138	12-M2-PI-0002-PRESSURE GAUGE(3).jpg	/data/storage/uploads/B-20260819-F58C90/12-M2-PI-0002/ab02a64eb77c420da3ab735633ecd34a.jpg	image/jpeg	4941527	2026-08-19 11:42:53.203688+00	2026-08-19 11:42:53.203688+00	0b4048d6188d28feb2e870b0c6e6d09fef61d73d17fea89e1d9785b851209643
157	138	12-M2-PI-0002-PRESSURE GAUGE(1).jpg	/data/storage/uploads/B-20260819-F58C90/12-M2-PI-0002/6662097e91414cc88fb4b5d1e06efb99.jpg	image/jpeg	5131484	2026-08-19 11:42:53.203688+00	2026-08-19 11:42:53.203688+00	c996f560eff13657c7c4de7bacff8b58c116e2b8fb9fe53529cfb2a0363a3af0
158	139	12-4020-FDI-21-0003-INFRARED FLAME DETECTOR.jpg	/data/storage/uploads/B-20260819-8DD594/12-4020-FDI-21-0003/d69573081aa143ffa19d5f84aaf9af1f.jpg	image/jpeg	1445292	2026-08-19 11:47:03.015804+00	2026-08-19 11:47:03.015804+00	d0e8c195927ff2d07cfa4536e49e5603310df5c3eb641f38e22eb255f224085a
159	140	12-4020-BV-0111-BALL VALVE(1).jpg	/data/storage/uploads/B-20260819-C2C95B/12-4020-BV-0111/4edc33340fe845789d6d5662473c1742.jpg	image/jpeg	1990214	2026-08-19 11:47:03.015804+00	2026-08-19 11:47:03.015804+00	472ec26e9bc616f5786d7cc58dbeb0d758cc5fb1be2f7be0b9aa71fd8cd752f0
160	140	12-4020-BV-0111-BALL VALVE(2).jpg	/data/storage/uploads/B-20260819-C2C95B/12-4020-BV-0111/b92ba4bf12b440d9bf0c37517c7f87ec.jpg	image/jpeg	2062380	2026-08-19 11:47:03.015804+00	2026-08-19 11:47:03.015804+00	0b18ade70234593dffcbe1a16b13ad4b6986755345b2246ef7c6aeb98deddf59
161	141	12-4020-BV-0083-BALL VALVE.jpg	/data/storage/uploads/B-20260819-64218E/12-4020-BV/98603df592bf49888437852370ba7bf6.jpg	image/jpeg	2109494	2026-08-19 11:47:03.015804+00	2026-08-19 11:47:03.015804+00	a851eaa7e2133cca22b99fc12d4d40b9cf068ff80206eea95aa47bdc966b4e1e
162	142	12-4020-NLV-0007-NEEDLE VALVE(1).jpg	/data/storage/uploads/B-20260819-8DD594/12-4020-NLV-0007/15fbe0007504487393d44483be0cfcfb.jpg	image/jpeg	5257996	2026-08-19 11:53:47.909541+00	2026-08-19 11:53:47.909541+00	53589e2997ab607cb5b4f681d0848cab7a8d97d12cc6499c9bda1ac63fe502ab
163	142	12-4020-NLV-0007-NEEDLE VALVE(2).jpg	/data/storage/uploads/B-20260819-8DD594/12-4020-NLV-0007/e363ff1f0d964ceebabea7441977742d.jpg	image/jpeg	5269722	2026-08-19 11:53:47.909541+00	2026-08-19 11:53:47.909541+00	00d7e067118222298850e4fb7f3ba7b94759e2268708047f76e6930e670bb2a2
164	143	16-GV-1982_VALVE,GATE.jpg	/data/storage/uploads/B-20260819-189961/16-GV-1982/bd90daebcb3e4519a2f33088906eb29f.jpg	image/jpeg	4952512	2026-08-19 12:04:27.7187+00	2026-08-19 12:04:27.7187+00	d4deedd98686f8843a00dd1825881801202a143c9173a2c7ba98628f7409aa66
165	144	PM-8981B MOTOR,PUMP.jpg	/data/storage/uploads/B-20260819-189961/PM/1adf500c1ef14370a7f9f963ab3c5989.jpg	image/jpeg	5605881	2026-08-19 12:04:27.7187+00	2026-08-19 12:04:27.7187+00	d8e350f8fb4f2281852c1834db353cbe2e654c6a1d503375c4bba6e5b36baff8
166	145	20-DZT-006-TRANSMITTER,DENSITY(1).jpg	/data/storage/uploads/B-20260819-4E7420/20-DZT-006/a303a91050a148e3b098d6e624545dc8.jpg	image/jpeg	5225874	2026-08-19 12:10:13.626795+00	2026-08-19 12:10:13.626795+00	b21c32c61413e5b9853952604dd4dccc5c5f95eec7967e9af82bb59b27fe5777
167	145	20-DZT-006-TRANSMITTER,DENSITY(2).jpg	/data/storage/uploads/B-20260819-4E7420/20-DZT-006/00c5762da90c4237bc165fec0ae04994.jpg	image/jpeg	5189918	2026-08-19 12:10:13.626795+00	2026-08-19 12:10:13.626795+00	f1bc372076730be7b526c036a1e7adb2d9283840b711901a982664907e48ba98
168	146	IMG_20250908_090046.jpg	/data/storage/uploads/B-20260820-18853E/35-SFX-015/79ad0e24d57e437ba78d6f51ddbce86b.jpg	image/jpeg	5179799	2026-08-20 11:25:53.082352+00	2026-08-20 11:25:53.082352+00	c7f29cc7d3828abef6420dece6a9c9eb01e3d5290e87210cf404b7c312a86941
169	147	IMG_20250113_120632.jpg	/data/storage/uploads/B-20260820-18853E/35-XL-01A-018/21d6e516392f4c1f89b04d38ae8c5ee2.jpg	image/jpeg	2910636	2026-08-20 11:25:53.082352+00	2026-08-20 11:25:53.082352+00	b98fe8bedb627298c2ca9f34df1ff24a2699513083c429048949c9c48651ad2f
170	147	IMG_20250113_120651.jpg	/data/storage/uploads/B-20260820-18853E/35-XL-01A-018/e19f252e3f544dd699d14c3f057a3957.jpg	image/jpeg	2457220	2026-08-20 11:25:53.082352+00	2026-08-20 11:25:53.082352+00	4032f3d1f7d308ba84ee0232c2f13b9612527c447f906ee439c56ae6e8b632f7
171	147	IMG_20250113_120723.jpg	/data/storage/uploads/B-20260820-18853E/35-XL-01A-018/a80c07d6ecad4760ba19fece3142c939.jpg	image/jpeg	2723055	2026-08-20 11:25:53.082352+00	2026-08-20 11:25:53.082352+00	f1a9908748ac895a0ee791fa2e2bd0ff3a3dc937a90e2866b4a8da539b104fad
172	147	IMG_20250113_120740.jpg	/data/storage/uploads/B-20260820-18853E/35-XL-01A-018/38cbda567d7e45d89621821af51ba6e0.jpg	image/jpeg	2046640	2026-08-20 11:25:53.082352+00	2026-08-20 11:25:53.082352+00	35963799b80e01a8312ede31a2898f8ff9a3c77edafd2a155043cd2025894fc8
173	148	IMG_20260112_094910.jpg	/data/storage/uploads/B-20260820-02C1F9/16-NRV-1268/c4d986b8ce454abebd8485bbb7135cc8.jpg	image/jpeg	5535502	2026-08-20 11:27:28.054792+00	2026-08-20 11:27:28.054792+00	0d31111ebb0d2fa0981592e586333706cc812a5061c03eda7de01e02a344ef5e
174	149	IMG_20220118_181356.jpg	/data/storage/uploads/B-20260820-02C1F9/35-GDF-01A-007/1fed726a6c09489cb35c08d9cd4b6070.jpg	image/jpeg	2507720	2026-08-20 11:27:28.054792+00	2026-08-20 11:27:28.054792+00	99eaee25b44bc191ff52ee1bc98157dd5cbdad88108e60b8ac832280258532d3
175	149	IMG_20220118_181638.jpg	/data/storage/uploads/B-20260820-02C1F9/35-GDF-01A-007/7ffcb3d154934d3a9abb1a03ecf05231.jpg	image/jpeg	1940889	2026-08-20 11:27:28.054792+00	2026-08-20 11:27:28.054792+00	623c82a878343cebc937eafa03baae998c8622fc406e587c53bda00b993a1ea0
176	150	002_IMG_20260521_123404.jpg	/data/storage/uploads/B-20260820-D1B169/72-PSV-003B/3d28f6712c384c0f815f2c5916fc2154.jpg	image/jpeg	114206	2026-08-20 11:29:26.751146+00	2026-08-20 11:29:26.751146+00	24243a159afe30e02b4736ec931ff9105b789e9e7b13d5b557a8706c1105e30d
177	151	001_IMG_20260525_095358.jpg	/data/storage/uploads/B-20260820-D1B169/2196JAM-CSS/79bb35adb0ed4708b4dc593235c14032.jpg	image/jpeg	834371	2026-08-20 11:29:26.751146+00	2026-08-20 11:29:26.751146+00	3679fa64babe0b300973fb7cc4bd495dff764e55445f379c2517bd0f2c7be3e2
178	152	002_IMG_20260611_084505.jpg	/data/storage/uploads/B-20260820-D1B169/73-PV-029/a3e47bcf5ebc41e4a3bbd05559c4f04e.jpg	image/jpeg	1639703	2026-08-20 11:29:26.751146+00	2026-08-20 11:29:26.751146+00	0ab403cd050adef7df9fad2651c69535c2150728c83952fce6160e0c4130557b
179	153	16-LIT-357-TRANSMITTER,LEVEL,INDICATING,NCR(1).jpg	/data/storage/uploads/B-20260820-E14389/16-LIT-357/b680365633744514ac9521880c741493.jpg	image/jpeg	4644455	2026-08-20 11:41:12.796729+00	2026-08-20 11:41:12.796729+00	a5cf3914af79315f701f3c9137b3c316c1595bf7953b284b0901dc4fc70dfb1d
180	153	16-LIT-357-TRANSMITTER,LEVEL,INDICATING,NCR(2).jpg	/data/storage/uploads/B-20260820-E14389/16-LIT-357/05663618a8d14fdbbafaeaa75dea71d8.jpg	image/jpeg	4952450	2026-08-20 11:41:12.796729+00	2026-08-20 11:41:12.796729+00	e0508c7b537e1a1f9d745be9d7e765fa9d366b7a173b1da56625f371c3a19715
181	153	16-LIT-357-TRANSMITTER,LEVEL,INDICATING,NCR(3).jpg	/data/storage/uploads/B-20260820-E14389/16-LIT-357/92de217f1d8e47f8b7ab8bee3a6b5378.jpg	image/jpeg	4965065	2026-08-20 11:41:12.796729+00	2026-08-20 11:41:12.796729+00	c6d7cfe10cf4ac2d0a12b834ce9183d7e6e6cf6622d2d960e5c2a4abd1433b51
182	154	72-LSL-102X-SWITCH,LEVEL.jpg	/data/storage/uploads/B-20260820-747BD8/72-LSL-102X/511c68104834441fb8302a55da26aec3.jpg	image/jpeg	302890	2026-08-20 11:42:06.473018+00	2026-08-20 11:42:06.473018+00	4c831dbd374e8bd1d5d9639bc9732732f4fe10334286390aa8a51d4a6eb36a45
183	155	73-TV-208X-VALVE,CONTROL,TEMPERATURE,3IN.jpg	/data/storage/uploads/B-20260820-747BD8/73-TV-208X/9d702c324ef34897a65f11ff328d4d1e.jpg	image/jpeg	2701328	2026-08-20 11:42:06.473018+00	2026-08-20 11:42:06.473018+00	1101b4d3d633a8b3b32fd938940311df98d648c6d201f61cf57a9fe6a53378cd
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: visioncore
--

COPY public.users (id, username, email, full_name, hashed_password, role, is_active, last_login_at, created_at, updated_at) FROM stdin;
3	user1	\N	User	$2b$12$bqEd4mpQ0PB395LrsJbD5.h42yJ67cIspKbBWk9m7dcF1DkAGZO8q	user	t	2026-08-27 04:48:58.231041+00	2026-08-14 05:04:58.166119+00	2026-08-27 04:48:57.857606+00
4	User1	\N	User1	$2b$12$.3paDhWZ0ykpIZ56lO4kwuvBONY7OjfpK9Ep2oaVOMfPAmgqIAzVu	user	t	2026-08-21 09:13:42.471287+00	2026-08-17 09:17:06.490047+00	2026-08-21 09:13:42.262043+00
2	user	\N	User	$2b$12$sTLESJiwFAY2VOErij1YYuoh1iHmMxURj.UOC8ACU0y.i2oQsIxc.	user	t	2026-08-25 09:08:23.026437+00	2026-08-07 11:01:39.413519+00	2026-08-25 09:08:22.831287+00
1	admin	\N	Admin	$2b$12$33v7OrwvSa0H2n8k9pE.K.hyYHyDURpy0EpJ8i/qkz0e7J6sZUDza	admin	t	2026-08-27 04:48:47.053096+00	2026-08-07 11:01:39.413519+00	2026-08-27 04:48:46.844962+00
\.


--
-- Name: activities_id_seq; Type: SEQUENCE SET; Schema: public; Owner: visioncore
--

SELECT pg_catalog.setval('public.activities_id_seq', 505, true);


--
-- Name: api_usage_id_seq; Type: SEQUENCE SET; Schema: public; Owner: visioncore
--

SELECT pg_catalog.setval('public.api_usage_id_seq', 99, true);


--
-- Name: asset_tags_id_seq; Type: SEQUENCE SET; Schema: public; Owner: visioncore
--

SELECT pg_catalog.setval('public.asset_tags_id_seq', 77, true);


--
-- Name: batch_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: visioncore
--

SELECT pg_catalog.setval('public.batch_items_id_seq', 155, true);


--
-- Name: batches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: visioncore
--

SELECT pg_catalog.setval('public.batches_id_seq', 97, true);


--
-- Name: org_credits_id_seq; Type: SEQUENCE SET; Schema: public; Owner: visioncore
--

SELECT pg_catalog.setval('public.org_credits_id_seq', 1, false);


--
-- Name: tag_images_id_seq; Type: SEQUENCE SET; Schema: public; Owner: visioncore
--

SELECT pg_catalog.setval('public.tag_images_id_seq', 183, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: visioncore
--

SELECT pg_catalog.setval('public.users_id_seq', 4, true);


--
-- Name: activities activities_pkey; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.activities
    ADD CONSTRAINT activities_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: api_usage api_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.api_usage
    ADD CONSTRAINT api_usage_pkey PRIMARY KEY (id);


--
-- Name: asset_tags asset_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.asset_tags
    ADD CONSTRAINT asset_tags_pkey PRIMARY KEY (id);


--
-- Name: batch_items batch_items_pkey; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.batch_items
    ADD CONSTRAINT batch_items_pkey PRIMARY KEY (id);


--
-- Name: batches batches_pkey; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_pkey PRIMARY KEY (id);


--
-- Name: org_credits org_credits_pkey; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.org_credits
    ADD CONSTRAINT org_credits_pkey PRIMARY KEY (id);


--
-- Name: tag_images tag_images_pkey; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.tag_images
    ADD CONSTRAINT tag_images_pkey PRIMARY KEY (id);


--
-- Name: asset_tags uq_asset_tags_tag_number; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.asset_tags
    ADD CONSTRAINT uq_asset_tags_tag_number UNIQUE (tag_number);


--
-- Name: batch_items uq_batch_tag; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.batch_items
    ADD CONSTRAINT uq_batch_tag UNIQUE (batch_id, tag_number);


--
-- Name: batches uq_batches_reference; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT uq_batches_reference UNIQUE (reference);


--
-- Name: users uq_users_email; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_email UNIQUE (email);


--
-- Name: users uq_users_username; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_username UNIQUE (username);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_activities_action; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_activities_action ON public.activities USING btree (action);


--
-- Name: ix_activities_created_at; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_activities_created_at ON public.activities USING btree (created_at DESC);


--
-- Name: ix_activities_tag_number; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_activities_tag_number ON public.activities USING btree (tag_number);


--
-- Name: ix_activities_user_id; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_activities_user_id ON public.activities USING btree (user_id);


--
-- Name: ix_api_usage_created_at; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_api_usage_created_at ON public.api_usage USING btree (created_at);


--
-- Name: ix_api_usage_tag_number; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_api_usage_tag_number ON public.api_usage USING btree (tag_number);


--
-- Name: ix_api_usage_user_id; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_api_usage_user_id ON public.api_usage USING btree (user_id);


--
-- Name: ix_asset_tags_tag_number; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_asset_tags_tag_number ON public.asset_tags USING btree (tag_number);


--
-- Name: ix_batch_items_batch_id; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_batch_items_batch_id ON public.batch_items USING btree (batch_id);


--
-- Name: ix_batch_items_tag_number; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_batch_items_tag_number ON public.batch_items USING btree (tag_number);


--
-- Name: ix_batches_reference; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_batches_reference ON public.batches USING btree (reference);


--
-- Name: ix_batches_user_id; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_batches_user_id ON public.batches USING btree (user_id);


--
-- Name: ix_tag_images_content_hash; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_tag_images_content_hash ON public.tag_images USING btree (content_hash);


--
-- Name: ix_tag_images_item_id; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_tag_images_item_id ON public.tag_images USING btree (item_id);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: visioncore
--

CREATE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: activities activities_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.activities
    ADD CONSTRAINT activities_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: api_usage api_usage_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.api_usage
    ADD CONSTRAINT api_usage_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: asset_tags asset_tags_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.asset_tags
    ADD CONSTRAINT asset_tags_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: asset_tags asset_tags_edited_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.asset_tags
    ADD CONSTRAINT asset_tags_edited_by_id_fkey FOREIGN KEY (edited_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: batch_items batch_items_asset_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.batch_items
    ADD CONSTRAINT batch_items_asset_tag_id_fkey FOREIGN KEY (asset_tag_id) REFERENCES public.asset_tags(id) ON DELETE SET NULL;


--
-- Name: batch_items batch_items_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.batch_items
    ADD CONSTRAINT batch_items_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.batches(id) ON DELETE CASCADE;


--
-- Name: batches batches_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: org_credits org_credits_updated_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.org_credits
    ADD CONSTRAINT org_credits_updated_by_user_id_fkey FOREIGN KEY (updated_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: tag_images tag_images_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: visioncore
--

ALTER TABLE ONLY public.tag_images
    ADD CONSTRAINT tag_images_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.batch_items(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict NuHgvs0W3HtROjZJRQPaqe4NILjydIo3sBu5yzetfCZVjhvyqA8QaLaqLAp3iU8

