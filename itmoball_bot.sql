--
-- PostgreSQL database dump
--

\restrict 8TvIxjxvDV2ibSE7ySAe6vbrrzGEawH6vIQeNWnl7mbD991RfgClzGthifmFSz2

-- Dumped from database version 18.0
-- Dumped by pg_dump version 18.0

-- Started on 2026-10-07 21:15:40

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 224 (class 1259 OID 16640)
-- Name: chat_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_sessions (
    id integer NOT NULL,
    user_id integer,
    topic character varying(30) NOT NULL,
    summary text DEFAULT ''::text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.chat_sessions OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 16639)
-- Name: chat_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chat_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_sessions_id_seq OWNER TO postgres;

--
-- TOC entry 5040 (class 0 OID 0)
-- Dependencies: 223
-- Name: chat_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chat_sessions_id_seq OWNED BY public.chat_sessions.id;


--
-- TOC entry 222 (class 1259 OID 16471)
-- Name: questions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.questions (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    is_ask character varying(50) NOT NULL,
    operator bigint,
    question text
);


ALTER TABLE public.questions OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 16470)
-- Name: questions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questions_id_seq OWNER TO postgres;

--
-- TOC entry 5041 (class 0 OID 0)
-- Dependencies: 221
-- Name: questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.questions_id_seq OWNED BY public.questions.id;


--
-- TOC entry 220 (class 1259 OID 16408)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    tg_id bigint,
    isu_id bigint,
    gender character varying(90)
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 16407)
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_user_id_seq OWNER TO postgres;

--
-- TOC entry 5042 (class 0 OID 0)
-- Dependencies: 219
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- TOC entry 4868 (class 2604 OID 16643)
-- Name: chat_sessions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions ALTER COLUMN id SET DEFAULT nextval('public.chat_sessions_id_seq'::regclass);


--
-- TOC entry 4867 (class 2604 OID 16474)
-- Name: questions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions ALTER COLUMN id SET DEFAULT nextval('public.questions_id_seq'::regclass);


--
-- TOC entry 4866 (class 2604 OID 16411)
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- TOC entry 5034 (class 0 OID 16640)
-- Dependencies: 224
-- Data for Name: chat_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chat_sessions (id, user_id, topic, summary, created_at, updated_at) FROM stdin;
1	1	dresscode	пользователь спросил, помнит ли ассистент предыдущий вопрос о возможности надеть чёрную бабочку; ассистент подтвердил, что помнит, и повторил свой ответ	2026-10-06 18:49:37.809509	2026-10-06 18:55:08.151111
2	1	music	пользователь спросил о предыдущем обсуждении музыки на балу, ассистент напомнил, что речь шла о классической музыке, включая произведения Гайдна, Бетховена и Штрауса	2026-10-06 19:02:21.006317	2026-10-06 19:02:33.817701
\.


--
-- TOC entry 5032 (class 0 OID 16471)
-- Dependencies: 222
-- Data for Name: questions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.questions (id, user_id, is_ask, operator, question) FROM stdin;
4	2	yes	1030853044	Test
6	2	yes	1030853044	Тестовое обращение
7	3	yes	1030853044	привет, организатор
8	1	yes	291826415	Могу ли я взять цветную бабочку ?
9	1	yes	1030853044	📷 Фото: C:\\Users\\batar\\YandexDisk-batarginegor\\ITMOball\\images\\user_1030853044_20251004_020604.jpg\n📝 Текст: Тест
10	1	yes	1030853044	📷 Фото: C:\\Users\\batar\\YandexDisk-batarginegor\\ITMOball\\images\\user_1030853044_20251004_021448.jpg\n📝 Текст: Тест
11	1	yes	1030853044	Привет
5	2	yes	1030853044	Test
12	1	yes	1030853044	Ку-ку
13	5	yes	1030853044	Здравствуйте, мы с партнером очень сильно хотели попасть на бал, но опоздали на регистрацию, подскажите, можно ли еще как-то попасть на бал?
\.


--
-- TOC entry 5030 (class 0 OID 16408)
-- Dependencies: 220
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (user_id, tg_id, isu_id, gender) FROM stdin;
1	1030853044	\N	М
2	7885423973	\N	Ж
3	291826415	\N	Ж
4	614195528	\N	М
5	932743965	\N	М
\.


--
-- TOC entry 5043 (class 0 OID 0)
-- Dependencies: 223
-- Name: chat_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.chat_sessions_id_seq', 2, true);


--
-- TOC entry 5044 (class 0 OID 0)
-- Dependencies: 221
-- Name: questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.questions_id_seq', 13, true);


--
-- TOC entry 5045 (class 0 OID 0)
-- Dependencies: 219
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_user_id_seq', 5, true);


--
-- TOC entry 4877 (class 2606 OID 16652)
-- Name: chat_sessions chat_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_pkey PRIMARY KEY (id);


--
-- TOC entry 4879 (class 2606 OID 16654)
-- Name: chat_sessions chat_sessions_user_id_topic_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_user_id_topic_key UNIQUE (user_id, topic);


--
-- TOC entry 4875 (class 2606 OID 16479)
-- Name: questions questions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_pkey PRIMARY KEY (id);


--
-- TOC entry 4873 (class 2606 OID 16414)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- TOC entry 4881 (class 2606 OID 16655)
-- Name: chat_sessions chat_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 4880 (class 2606 OID 16500)
-- Name: questions fk_user; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON UPDATE CASCADE ON DELETE CASCADE;


-- Completed on 2026-10-07 21:15:41

--
-- PostgreSQL database dump complete
--

\unrestrict 8TvIxjxvDV2ibSE7ySAe6vbrrzGEawH6vIQeNWnl7mbD991RfgClzGthifmFSz2

