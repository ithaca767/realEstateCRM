--
-- PostgreSQL database dump
--

\restrict t3Ooa8kgWKaJOpbVHTfqLhsBwmVIto3KcJV9PLrwkPYv6pmCAOsgDR9IYBzeyak

-- Dumped from database version 18.1 (Homebrew)
-- Dumped by pg_dump version 18.1 (Homebrew)

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
-- Name: brand_settings; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.brand_settings (
    id integer NOT NULL,
    user_id integer NOT NULL,
    brokerage_name text,
    logo_url text,
    headshot_url text,
    primary_color text,
    disclaimer_text text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.brand_settings OWNER TO dennisfotopoulos;

--
-- Name: brand_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.brand_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.brand_settings_id_seq OWNER TO dennisfotopoulos;

--
-- Name: brand_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.brand_settings_id_seq OWNED BY public.brand_settings.id;


--
-- Name: buyer_profiles; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.buyer_profiles (
    id integer NOT NULL,
    contact_id integer NOT NULL,
    timeframe text,
    min_price integer,
    max_price integer,
    areas text,
    property_types text,
    preapproval_status text,
    lender_name text,
    referral_source text,
    notes text,
    property_type text,
    cis_signed boolean,
    buyer_agreement_signed boolean,
    wire_fraud_notice_signed boolean,
    dual_agency_consent_signed boolean,
    buyer_attorney_name text,
    buyer_attorney_email text,
    buyer_attorney_phone text,
    buyer_attorney_referred boolean,
    buyer_lender_email text,
    buyer_lender_phone text,
    buyer_lender_referred boolean,
    buyer_inspector_name text,
    buyer_inspector_email text,
    buyer_inspector_phone text,
    buyer_inspector_referred boolean,
    other_professionals text,
    preapproval_letter_received boolean,
    proof_of_funds_received boolean,
    photo_id_received boolean
);


ALTER TABLE public.buyer_profiles OWNER TO dennisfotopoulos;

--
-- Name: buyer_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.buyer_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.buyer_profiles_id_seq OWNER TO dennisfotopoulos;

--
-- Name: buyer_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.buyer_profiles_id_seq OWNED BY public.buyer_profiles.id;


--
-- Name: buyer_properties; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.buyer_properties (
    id integer NOT NULL,
    buyer_profile_id integer NOT NULL,
    address_line text,
    city text,
    state text,
    postal_code text,
    offer_status text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT buyer_properties_offer_status_check CHECK ((offer_status = ANY (ARRAY['considering'::text, 'accepted'::text, 'lost'::text, 'attorney review'::text, 'under contract'::text])))
);


ALTER TABLE public.buyer_properties OWNER TO dennisfotopoulos;

--
-- Name: buyer_properties_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.buyer_properties_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.buyer_properties_id_seq OWNER TO dennisfotopoulos;

--
-- Name: buyer_properties_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.buyer_properties_id_seq OWNED BY public.buyer_properties.id;


--
-- Name: contact_associations; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.contact_associations (
    id integer NOT NULL,
    user_id integer NOT NULL,
    contact_id_primary integer NOT NULL,
    contact_id_related integer NOT NULL,
    relationship_type character varying(40),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    notes text,
    CONSTRAINT chk_no_self_assoc CHECK ((contact_id_primary <> contact_id_related))
);


ALTER TABLE public.contact_associations OWNER TO dennisfotopoulos;

--
-- Name: contact_associations_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.contact_associations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.contact_associations_id_seq OWNER TO dennisfotopoulos;

--
-- Name: contact_associations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.contact_associations_id_seq OWNED BY public.contact_associations.id;


--
-- Name: contact_special_dates; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.contact_special_dates (
    id integer NOT NULL,
    contact_id integer NOT NULL,
    label text NOT NULL,
    special_date date NOT NULL,
    is_recurring boolean DEFAULT true NOT NULL,
    notes text,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.contact_special_dates OWNER TO dennisfotopoulos;

--
-- Name: contact_special_dates_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.contact_special_dates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.contact_special_dates_id_seq OWNER TO dennisfotopoulos;

--
-- Name: contact_special_dates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.contact_special_dates_id_seq OWNED BY public.contact_special_dates.id;


--
-- Name: contacts; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.contacts (
    id integer NOT NULL,
    name text NOT NULL,
    email text,
    phone text,
    lead_type text,
    pipeline_stage text,
    price_min integer,
    price_max integer,
    target_area text,
    source text,
    priority text,
    last_contacted text,
    next_follow_up text,
    notes text,
    first_name text,
    last_name text,
    current_address text,
    subject_address text,
    current_city text,
    current_state text,
    current_zip text,
    subject_city text,
    subject_state text,
    subject_zip text,
    next_follow_up_time text,
    working_with_agent boolean,
    agent_name text,
    agent_phone text,
    agent_brokerage text,
    lead_source text,
    last_open_house_id integer,
    user_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    archived_at timestamp without time zone,
    contact_state text DEFAULT 'active'::text NOT NULL,
    newsletter_opt_in boolean DEFAULT false NOT NULL,
    newsletter_opt_in_date timestamp without time zone,
    newsletter_source text,
    CONSTRAINT contacts_contact_state_check CHECK ((contact_state = ANY (ARRAY['imported'::text, 'inactive'::text, 'active'::text])))
);


ALTER TABLE public.contacts OWNER TO dennisfotopoulos;

--
-- Name: contacts_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.contacts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.contacts_id_seq OWNER TO dennisfotopoulos;

--
-- Name: contacts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.contacts_id_seq OWNED BY public.contacts.id;


--
-- Name: engagements; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.engagements (
    id integer NOT NULL,
    user_id integer NOT NULL,
    contact_id integer NOT NULL,
    engagement_type character varying(80) DEFAULT 'call'::character varying NOT NULL,
    occurred_at timestamp without time zone DEFAULT now() NOT NULL,
    outcome text,
    notes text,
    transcript_raw text,
    summary_clean text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    requires_follow_up boolean DEFAULT false NOT NULL,
    follow_up_due_at timestamp with time zone,
    follow_up_completed boolean DEFAULT false NOT NULL,
    follow_up_completed_at timestamp without time zone
);


ALTER TABLE public.engagements OWNER TO dennisfotopoulos;

--
-- Name: engagements_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.engagements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.engagements_id_seq OWNER TO dennisfotopoulos;

--
-- Name: engagements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.engagements_id_seq OWNED BY public.engagements.id;


--
-- Name: interactions; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.interactions (
    id integer NOT NULL,
    contact_id integer NOT NULL,
    kind text NOT NULL,
    happened_at date,
    notes text,
    time_of_day text,
    completed_at timestamp without time zone,
    is_completed boolean DEFAULT false NOT NULL,
    due_at timestamp with time zone,
    notified boolean DEFAULT false,
    user_id integer NOT NULL
);


ALTER TABLE public.interactions OWNER TO dennisfotopoulos;

--
-- Name: interactions_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.interactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.interactions_id_seq OWNER TO dennisfotopoulos;

--
-- Name: interactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.interactions_id_seq OWNED BY public.interactions.id;


--
-- Name: listing_checklist_items; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.listing_checklist_items (
    id integer NOT NULL,
    contact_id integer NOT NULL,
    item_key text NOT NULL,
    label text NOT NULL,
    due_date date,
    is_complete boolean DEFAULT false NOT NULL,
    completed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.listing_checklist_items OWNER TO dennisfotopoulos;

--
-- Name: listing_checklist_items_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.listing_checklist_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.listing_checklist_items_id_seq OWNER TO dennisfotopoulos;

--
-- Name: listing_checklist_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.listing_checklist_items_id_seq OWNED BY public.listing_checklist_items.id;


--
-- Name: newsletter_signup_links; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.newsletter_signup_links (
    id integer NOT NULL,
    created_by_user_id integer NOT NULL,
    title text NOT NULL,
    public_token text NOT NULL,
    redirect_url text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.newsletter_signup_links OWNER TO dennisfotopoulos;

--
-- Name: newsletter_signup_links_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.newsletter_signup_links_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.newsletter_signup_links_id_seq OWNER TO dennisfotopoulos;

--
-- Name: newsletter_signup_links_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.newsletter_signup_links_id_seq OWNED BY public.newsletter_signup_links.id;


--
-- Name: open_house_signins; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.open_house_signins (
    id integer NOT NULL,
    open_house_id integer NOT NULL,
    contact_id integer,
    first_name text,
    last_name text,
    email text,
    phone text,
    working_with_agent boolean,
    agent_name text,
    agent_phone text,
    agent_brokerage text,
    looking_to_buy boolean,
    looking_to_sell boolean,
    timeline text,
    notes text,
    consent_to_contact boolean DEFAULT true,
    submitted_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.open_house_signins OWNER TO dennisfotopoulos;

--
-- Name: open_house_signins_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.open_house_signins_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.open_house_signins_id_seq OWNER TO dennisfotopoulos;

--
-- Name: open_house_signins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.open_house_signins_id_seq OWNED BY public.open_house_signins.id;


--
-- Name: open_houses; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.open_houses (
    id integer NOT NULL,
    created_by_user_id integer NOT NULL,
    address_line1 text NOT NULL,
    city text NOT NULL,
    state text DEFAULT 'NJ'::text NOT NULL,
    zip text NOT NULL,
    start_datetime timestamp without time zone NOT NULL,
    end_datetime timestamp without time zone NOT NULL,
    public_token text NOT NULL,
    house_photo_url text,
    notes text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.open_houses OWNER TO dennisfotopoulos;

--
-- Name: open_houses_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.open_houses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.open_houses_id_seq OWNER TO dennisfotopoulos;

--
-- Name: open_houses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.open_houses_id_seq OWNED BY public.open_houses.id;


--
-- Name: password_resets; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.password_resets (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id integer NOT NULL,
    token_hash text NOT NULL,
    request_ip text,
    request_user_agent text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    revoked_at timestamp with time zone
);


ALTER TABLE public.password_resets OWNER TO dennisfotopoulos;

--
-- Name: professionals; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.professionals (
    id integer NOT NULL,
    name text NOT NULL,
    company text,
    phone text,
    email text,
    category text,
    grade text NOT NULL,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_id integer NOT NULL
);


ALTER TABLE public.professionals OWNER TO dennisfotopoulos;

--
-- Name: professionals_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.professionals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.professionals_id_seq OWNER TO dennisfotopoulos;

--
-- Name: professionals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.professionals_id_seq OWNED BY public.professionals.id;


--
-- Name: related_contacts; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.related_contacts (
    id integer NOT NULL,
    contact_id integer NOT NULL,
    related_name text NOT NULL,
    relationship text,
    email text,
    phone text,
    notes text
);


ALTER TABLE public.related_contacts OWNER TO dennisfotopoulos;

--
-- Name: related_contacts_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.related_contacts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.related_contacts_id_seq OWNER TO dennisfotopoulos;

--
-- Name: related_contacts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.related_contacts_id_seq OWNED BY public.related_contacts.id;


--
-- Name: seller_profiles; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.seller_profiles (
    id integer NOT NULL,
    contact_id integer NOT NULL,
    timeframe text,
    motivation text,
    estimated_price integer,
    property_address text,
    condition_notes text,
    referral_source text,
    notes text,
    property_type text,
    seller_attorney_name text,
    seller_attorney_email text,
    seller_attorney_phone text,
    seller_attorney_referred boolean,
    seller_lender_name text,
    seller_lender_email text,
    seller_lender_phone text,
    seller_lender_referred boolean,
    seller_inspector_name text,
    seller_inspector_email text,
    seller_inspector_phone text,
    seller_inspector_referred boolean,
    other_professionals text
);


ALTER TABLE public.seller_profiles OWNER TO dennisfotopoulos;

--
-- Name: seller_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.seller_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seller_profiles_id_seq OWNER TO dennisfotopoulos;

--
-- Name: seller_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.seller_profiles_id_seq OWNED BY public.seller_profiles.id;


--
-- Name: task_document_links; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.task_document_links (
    id integer NOT NULL,
    user_id integer NOT NULL,
    task_id integer NOT NULL,
    url text NOT NULL,
    provider character varying(30) DEFAULT 'other'::character varying NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT task_document_links_provider_check CHECK (((provider)::text = ANY ((ARRAY['google_drive'::character varying, 'icloud'::character varying, 'dropbox'::character varying, 'onedrive'::character varying, 'other'::character varying])::text[])))
);


ALTER TABLE public.task_document_links OWNER TO dennisfotopoulos;

--
-- Name: task_document_links_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.task_document_links_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.task_document_links_id_seq OWNER TO dennisfotopoulos;

--
-- Name: task_document_links_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.task_document_links_id_seq OWNED BY public.task_document_links.id;


--
-- Name: tasks; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.tasks (
    id integer NOT NULL,
    user_id integer NOT NULL,
    contact_id integer,
    transaction_id integer,
    engagement_id integer,
    professional_id integer,
    title character varying(255) NOT NULL,
    description text,
    task_type character varying(50),
    status character varying(30) DEFAULT 'open'::character varying NOT NULL,
    priority character varying(20),
    due_date date,
    due_at timestamp with time zone,
    snoozed_until timestamp with time zone,
    completed_at timestamp with time zone,
    canceled_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tasks_status_check CHECK (((status)::text = ANY ((ARRAY['open'::character varying, 'completed'::character varying, 'snoozed'::character varying, 'canceled'::character varying])::text[])))
);


ALTER TABLE public.tasks OWNER TO dennisfotopoulos;

--
-- Name: tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tasks_id_seq OWNER TO dennisfotopoulos;

--
-- Name: tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.tasks_id_seq OWNED BY public.tasks.id;


--
-- Name: templates; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.templates (
    id integer NOT NULL,
    title text NOT NULL,
    category text DEFAULT 'General'::text NOT NULL,
    delivery_type text DEFAULT 'either'::text NOT NULL,
    body text DEFAULT ''::text NOT NULL,
    notes text DEFAULT ''::text NOT NULL,
    is_locked boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    archived_at timestamp with time zone
);


ALTER TABLE public.templates OWNER TO dennisfotopoulos;

--
-- Name: templates_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.templates_id_seq OWNER TO dennisfotopoulos;

--
-- Name: templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.templates_id_seq OWNED BY public.templates.id;


--
-- Name: transaction_deadlines; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.transaction_deadlines (
    id integer NOT NULL,
    user_id integer NOT NULL,
    transaction_id integer NOT NULL,
    name character varying(80) NOT NULL,
    due_date date,
    is_done boolean DEFAULT false NOT NULL,
    notes text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.transaction_deadlines OWNER TO dennisfotopoulos;

--
-- Name: transaction_deadlines_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.transaction_deadlines_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transaction_deadlines_id_seq OWNER TO dennisfotopoulos;

--
-- Name: transaction_deadlines_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.transaction_deadlines_id_seq OWNED BY public.transaction_deadlines.id;


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    contact_id integer NOT NULL,
    transaction_type character varying(20) DEFAULT 'unknown'::character varying NOT NULL,
    address_line character varying(120),
    city character varying(80),
    state character varying(40),
    postal_code character varying(20),
    listing_status character varying(30) DEFAULT 'draft'::character varying NOT NULL,
    offer_status character varying(30) DEFAULT 'draft'::character varying NOT NULL,
    notes text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    status character varying(30) DEFAULT 'draft'::character varying NOT NULL,
    address text,
    primary_contact_id integer,
    secondary_contact_id integer,
    list_price numeric(12,2),
    offer_price numeric(12,2),
    accepted_price numeric(12,2),
    closed_price numeric(12,2),
    list_date date,
    attorney_review_end_date date,
    inspection_deadline date,
    financing_contingency_date date,
    appraisal_deadline date,
    mortgage_commitment_date date,
    expected_close_date date,
    actual_close_date date,
    status_changed_at timestamp without time zone,
    transaction_context text,
    transaction_context_updated_at timestamp with time zone,
    CONSTRAINT transactions_listing_status_check CHECK (((listing_status)::text = ANY (ARRAY['draft'::text, 'coming_soon'::text, 'active'::text, 'under_contract'::text, 'back_on_market'::text, 'withdrawn'::text, 'expired'::text, 'closed'::text]))),
    CONSTRAINT transactions_offer_status_check CHECK (((offer_status)::text = ANY (ARRAY['draft'::text, 'submitted'::text, 'countered'::text, 'accepted'::text, 'rejected'::text, 'withdrawn'::text, 'under_contract'::text, 'closed'::text]))),
    CONSTRAINT transactions_status_check CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'coming_soon'::character varying, 'active'::character varying, 'attorney_review'::character varying, 'pending_uc'::character varying, 'closed'::character varying, 'temp_off_market'::character varying, 'withdrawn'::character varying, 'canceled'::character varying, 'expired'::character varying])::text[]))),
    CONSTRAINT transactions_transaction_type_check CHECK (((transaction_type)::text = ANY (ARRAY[('buy'::character varying)::text, ('sell'::character varying)::text, ('rent'::character varying)::text, ('lease'::character varying)::text, ('unknown'::character varying)::text])))
);


ALTER TABLE public.transactions OWNER TO dennisfotopoulos;

--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transactions_id_seq OWNER TO dennisfotopoulos;

--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- Name: user_invites; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.user_invites (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    invited_email text NOT NULL,
    role text DEFAULT 'user'::text NOT NULL,
    token_hash text NOT NULL,
    invited_by_user_id integer NOT NULL,
    used_by_user_id integer,
    note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    revoked_at timestamp with time zone,
    CONSTRAINT user_invites_role_check CHECK ((role = ANY (ARRAY['owner'::text, 'user'::text])))
);


ALTER TABLE public.user_invites OWNER TO dennisfotopoulos;

--
-- Name: users; Type: TABLE; Schema: public; Owner: dennisfotopoulos
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    first_name text,
    last_name text,
    role text DEFAULT 'owner'::text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    last_login_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO dennisfotopoulos;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: dennisfotopoulos
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO dennisfotopoulos;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dennisfotopoulos
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: brand_settings id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.brand_settings ALTER COLUMN id SET DEFAULT nextval('public.brand_settings_id_seq'::regclass);


--
-- Name: buyer_profiles id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.buyer_profiles ALTER COLUMN id SET DEFAULT nextval('public.buyer_profiles_id_seq'::regclass);


--
-- Name: buyer_properties id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.buyer_properties ALTER COLUMN id SET DEFAULT nextval('public.buyer_properties_id_seq'::regclass);


--
-- Name: contact_associations id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.contact_associations ALTER COLUMN id SET DEFAULT nextval('public.contact_associations_id_seq'::regclass);


--
-- Name: contact_special_dates id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.contact_special_dates ALTER COLUMN id SET DEFAULT nextval('public.contact_special_dates_id_seq'::regclass);


--
-- Name: contacts id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.contacts ALTER COLUMN id SET DEFAULT nextval('public.contacts_id_seq'::regclass);


--
-- Name: engagements id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.engagements ALTER COLUMN id SET DEFAULT nextval('public.engagements_id_seq'::regclass);


--
-- Name: interactions id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.interactions ALTER COLUMN id SET DEFAULT nextval('public.interactions_id_seq'::regclass);


--
-- Name: listing_checklist_items id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.listing_checklist_items ALTER COLUMN id SET DEFAULT nextval('public.listing_checklist_items_id_seq'::regclass);


--
-- Name: newsletter_signup_links id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.newsletter_signup_links ALTER COLUMN id SET DEFAULT nextval('public.newsletter_signup_links_id_seq'::regclass);


--
-- Name: open_house_signins id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.open_house_signins ALTER COLUMN id SET DEFAULT nextval('public.open_house_signins_id_seq'::regclass);


--
-- Name: open_houses id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.open_houses ALTER COLUMN id SET DEFAULT nextval('public.open_houses_id_seq'::regclass);


--
-- Name: professionals id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.professionals ALTER COLUMN id SET DEFAULT nextval('public.professionals_id_seq'::regclass);


--
-- Name: related_contacts id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.related_contacts ALTER COLUMN id SET DEFAULT nextval('public.related_contacts_id_seq'::regclass);


--
-- Name: seller_profiles id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.seller_profiles ALTER COLUMN id SET DEFAULT nextval('public.seller_profiles_id_seq'::regclass);


--
-- Name: task_document_links id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.task_document_links ALTER COLUMN id SET DEFAULT nextval('public.task_document_links_id_seq'::regclass);


--
-- Name: tasks id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.tasks ALTER COLUMN id SET DEFAULT nextval('public.tasks_id_seq'::regclass);


--
-- Name: templates id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.templates ALTER COLUMN id SET DEFAULT nextval('public.templates_id_seq'::regclass);


--
-- Name: transaction_deadlines id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.transaction_deadlines ALTER COLUMN id SET DEFAULT nextval('public.transaction_deadlines_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: brand_settings brand_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.brand_settings
    ADD CONSTRAINT brand_settings_pkey PRIMARY KEY (id);


--
-- Name: brand_settings brand_settings_user_id_key; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.brand_settings
    ADD CONSTRAINT brand_settings_user_id_key UNIQUE (user_id);


--
-- Name: buyer_profiles buyer_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.buyer_profiles
    ADD CONSTRAINT buyer_profiles_pkey PRIMARY KEY (id);


--
-- Name: buyer_properties buyer_properties_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.buyer_properties
    ADD CONSTRAINT buyer_properties_pkey PRIMARY KEY (id);


--
-- Name: contact_associations contact_associations_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.contact_associations
    ADD CONSTRAINT contact_associations_pkey PRIMARY KEY (id);


--
-- Name: contact_special_dates contact_special_dates_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.contact_special_dates
    ADD CONSTRAINT contact_special_dates_pkey PRIMARY KEY (id);


--
-- Name: contacts contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.contacts
    ADD CONSTRAINT contacts_pkey PRIMARY KEY (id);


--
-- Name: engagements engagements_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.engagements
    ADD CONSTRAINT engagements_pkey PRIMARY KEY (id);


--
-- Name: interactions interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.interactions
    ADD CONSTRAINT interactions_pkey PRIMARY KEY (id);


--
-- Name: listing_checklist_items listing_checklist_items_contact_id_item_key_key; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.listing_checklist_items
    ADD CONSTRAINT listing_checklist_items_contact_id_item_key_key UNIQUE (contact_id, item_key);


--
-- Name: listing_checklist_items listing_checklist_items_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.listing_checklist_items
    ADD CONSTRAINT listing_checklist_items_pkey PRIMARY KEY (id);


--
-- Name: newsletter_signup_links newsletter_signup_links_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.newsletter_signup_links
    ADD CONSTRAINT newsletter_signup_links_pkey PRIMARY KEY (id);


--
-- Name: newsletter_signup_links newsletter_signup_links_public_token_key; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.newsletter_signup_links
    ADD CONSTRAINT newsletter_signup_links_public_token_key UNIQUE (public_token);


--
-- Name: open_house_signins open_house_signins_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.open_house_signins
    ADD CONSTRAINT open_house_signins_pkey PRIMARY KEY (id);


--
-- Name: open_houses open_houses_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.open_houses
    ADD CONSTRAINT open_houses_pkey PRIMARY KEY (id);


--
-- Name: open_houses open_houses_public_token_key; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.open_houses
    ADD CONSTRAINT open_houses_public_token_key UNIQUE (public_token);


--
-- Name: password_resets password_resets_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_pkey PRIMARY KEY (id);


--
-- Name: professionals professionals_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.professionals
    ADD CONSTRAINT professionals_pkey PRIMARY KEY (id);


--
-- Name: related_contacts related_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.related_contacts
    ADD CONSTRAINT related_contacts_pkey PRIMARY KEY (id);


--
-- Name: seller_profiles seller_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.seller_profiles
    ADD CONSTRAINT seller_profiles_pkey PRIMARY KEY (id);


--
-- Name: task_document_links task_document_links_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.task_document_links
    ADD CONSTRAINT task_document_links_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: templates templates_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.templates
    ADD CONSTRAINT templates_pkey PRIMARY KEY (id);


--
-- Name: transaction_deadlines transaction_deadlines_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.transaction_deadlines
    ADD CONSTRAINT transaction_deadlines_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: user_invites user_invites_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.user_invites
    ADD CONSTRAINT user_invites_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_contact_special_dates_contact_id; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_contact_special_dates_contact_id ON public.contact_special_dates USING btree (contact_id);


--
-- Name: idx_contact_special_dates_date; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_contact_special_dates_date ON public.contact_special_dates USING btree (special_date);


--
-- Name: idx_contacts_user_archived; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_contacts_user_archived ON public.contacts USING btree (user_id, archived_at);


--
-- Name: idx_contacts_user_id; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_contacts_user_id ON public.contacts USING btree (user_id);


--
-- Name: idx_engagements_followup_due; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_engagements_followup_due ON public.engagements USING btree (user_id, follow_up_due_at) WHERE ((requires_follow_up = true) AND (follow_up_completed = false) AND (follow_up_due_at IS NOT NULL));


--
-- Name: idx_engagements_user_contact_occurred; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_engagements_user_contact_occurred ON public.engagements USING btree (user_id, contact_id, occurred_at DESC);


--
-- Name: idx_interactions_user_happened; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_interactions_user_happened ON public.interactions USING btree (user_id, happened_at DESC);


--
-- Name: idx_listing_checklist_contact_id; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_listing_checklist_contact_id ON public.listing_checklist_items USING btree (contact_id);


--
-- Name: idx_listing_checklist_due_date; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_listing_checklist_due_date ON public.listing_checklist_items USING btree (due_date);


--
-- Name: idx_listing_checklist_incomplete_due; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_listing_checklist_incomplete_due ON public.listing_checklist_items USING btree (is_complete, due_date);


--
-- Name: idx_newsletter_links_user_id; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_newsletter_links_user_id ON public.newsletter_signup_links USING btree (created_by_user_id);


--
-- Name: idx_professionals_user_id; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_professionals_user_id ON public.professionals USING btree (user_id);


--
-- Name: idx_task_doclinks_task; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_task_doclinks_task ON public.task_document_links USING btree (task_id);


--
-- Name: idx_task_doclinks_user; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_task_doclinks_user ON public.task_document_links USING btree (user_id);


--
-- Name: idx_tasks_contact; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_tasks_contact ON public.tasks USING btree (user_id, contact_id);


--
-- Name: idx_tasks_engagement; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_tasks_engagement ON public.tasks USING btree (user_id, engagement_id);


--
-- Name: idx_tasks_professional; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_tasks_professional ON public.tasks USING btree (user_id, professional_id);


--
-- Name: idx_tasks_transaction; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_tasks_transaction ON public.tasks USING btree (user_id, transaction_id);


--
-- Name: idx_tasks_user_due_at; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_tasks_user_due_at ON public.tasks USING btree (user_id, due_at);


--
-- Name: idx_tasks_user_status_due; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_tasks_user_status_due ON public.tasks USING btree (user_id, status, due_date);


--
-- Name: idx_templates_archived_at; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_templates_archived_at ON public.templates USING btree (archived_at);


--
-- Name: idx_templates_category; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_templates_category ON public.templates USING btree (category);


--
-- Name: idx_templates_locked; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_templates_locked ON public.templates USING btree (is_locked);


--
-- Name: idx_templates_updated_at; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_templates_updated_at ON public.templates USING btree (updated_at DESC);


--
-- Name: idx_transaction_deadlines_transaction_id; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_transaction_deadlines_transaction_id ON public.transaction_deadlines USING btree (transaction_id);


--
-- Name: idx_transaction_deadlines_tx_id; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_transaction_deadlines_tx_id ON public.transaction_deadlines USING btree (transaction_id);


--
-- Name: idx_transaction_deadlines_user_due; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_transaction_deadlines_user_due ON public.transaction_deadlines USING btree (user_id, due_date);


--
-- Name: idx_transaction_deadlines_user_id; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_transaction_deadlines_user_id ON public.transaction_deadlines USING btree (user_id);


--
-- Name: idx_transactions_contact_id; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_transactions_contact_id ON public.transactions USING btree (contact_id);


--
-- Name: idx_transactions_listing_status; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_transactions_listing_status ON public.transactions USING btree (listing_status);


--
-- Name: idx_transactions_offer_status; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_transactions_offer_status ON public.transactions USING btree (offer_status);


--
-- Name: idx_transactions_primary_contact_id; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_transactions_primary_contact_id ON public.transactions USING btree (primary_contact_id);


--
-- Name: idx_transactions_secondary_contact_id; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_transactions_secondary_contact_id ON public.transactions USING btree (secondary_contact_id);


--
-- Name: idx_transactions_status; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_transactions_status ON public.transactions USING btree (status);


--
-- Name: idx_transactions_user_id; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX idx_transactions_user_id ON public.transactions USING btree (user_id);


--
-- Name: ix_contact_assoc_primary; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX ix_contact_assoc_primary ON public.contact_associations USING btree (user_id, contact_id_primary);


--
-- Name: ix_contact_assoc_related; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX ix_contact_assoc_related ON public.contact_associations USING btree (user_id, contact_id_related);


--
-- Name: password_resets_expires_at_idx; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX password_resets_expires_at_idx ON public.password_resets USING btree (expires_at);


--
-- Name: password_resets_token_hash_uq; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE UNIQUE INDEX password_resets_token_hash_uq ON public.password_resets USING btree (token_hash);


--
-- Name: password_resets_user_id_idx; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX password_resets_user_id_idx ON public.password_resets USING btree (user_id);


--
-- Name: user_invites_active_idx; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX user_invites_active_idx ON public.user_invites USING btree (created_at) WHERE ((used_at IS NULL) AND (revoked_at IS NULL));


--
-- Name: user_invites_expires_at_idx; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX user_invites_expires_at_idx ON public.user_invites USING btree (expires_at);


--
-- Name: user_invites_invited_email_idx; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE INDEX user_invites_invited_email_idx ON public.user_invites USING btree (invited_email);


--
-- Name: user_invites_token_hash_uq; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE UNIQUE INDEX user_invites_token_hash_uq ON public.user_invites USING btree (token_hash);


--
-- Name: ux_contact_assoc_pair; Type: INDEX; Schema: public; Owner: dennisfotopoulos
--

CREATE UNIQUE INDEX ux_contact_assoc_pair ON public.contact_associations USING btree (user_id, contact_id_primary, contact_id_related);


--
-- Name: buyer_profiles buyer_profiles_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.buyer_profiles
    ADD CONSTRAINT buyer_profiles_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contacts(id) ON DELETE RESTRICT;


--
-- Name: buyer_properties buyer_properties_buyer_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.buyer_properties
    ADD CONSTRAINT buyer_properties_buyer_profile_id_fkey FOREIGN KEY (buyer_profile_id) REFERENCES public.buyer_profiles(id) ON DELETE CASCADE;


--
-- Name: contact_associations contact_associations_contact_id_primary_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.contact_associations
    ADD CONSTRAINT contact_associations_contact_id_primary_fkey FOREIGN KEY (contact_id_primary) REFERENCES public.contacts(id) ON DELETE RESTRICT;


--
-- Name: contact_associations contact_associations_contact_id_related_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.contact_associations
    ADD CONSTRAINT contact_associations_contact_id_related_fkey FOREIGN KEY (contact_id_related) REFERENCES public.contacts(id) ON DELETE RESTRICT;


--
-- Name: contact_associations contact_associations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.contact_associations
    ADD CONSTRAINT contact_associations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: contact_special_dates contact_special_dates_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.contact_special_dates
    ADD CONSTRAINT contact_special_dates_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contacts(id) ON DELETE RESTRICT;


--
-- Name: engagements engagements_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.engagements
    ADD CONSTRAINT engagements_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contacts(id) ON DELETE RESTRICT;


--
-- Name: engagements engagements_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.engagements
    ADD CONSTRAINT engagements_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: interactions interactions_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.interactions
    ADD CONSTRAINT interactions_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contacts(id) ON DELETE RESTRICT;


--
-- Name: interactions interactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.interactions
    ADD CONSTRAINT interactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: listing_checklist_items listing_checklist_items_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.listing_checklist_items
    ADD CONSTRAINT listing_checklist_items_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contacts(id) ON DELETE RESTRICT;


--
-- Name: newsletter_signup_links newsletter_signup_links_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.newsletter_signup_links
    ADD CONSTRAINT newsletter_signup_links_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: open_house_signins open_house_signins_open_house_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.open_house_signins
    ADD CONSTRAINT open_house_signins_open_house_id_fkey FOREIGN KEY (open_house_id) REFERENCES public.open_houses(id) ON DELETE CASCADE;


--
-- Name: password_resets password_resets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: related_contacts related_contacts_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.related_contacts
    ADD CONSTRAINT related_contacts_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contacts(id) ON DELETE RESTRICT;


--
-- Name: seller_profiles seller_profiles_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.seller_profiles
    ADD CONSTRAINT seller_profiles_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contacts(id) ON DELETE RESTRICT;


--
-- Name: task_document_links task_document_links_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.task_document_links
    ADD CONSTRAINT task_document_links_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_document_links task_document_links_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.task_document_links
    ADD CONSTRAINT task_document_links_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contacts(id) ON DELETE SET NULL;


--
-- Name: tasks tasks_engagement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_engagement_id_fkey FOREIGN KEY (engagement_id) REFERENCES public.engagements(id) ON DELETE SET NULL;


--
-- Name: tasks tasks_professional_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_professional_id_fkey FOREIGN KEY (professional_id) REFERENCES public.professionals(id) ON DELETE SET NULL;


--
-- Name: tasks tasks_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.transactions(id) ON DELETE SET NULL;


--
-- Name: tasks tasks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: transaction_deadlines transaction_deadlines_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.transaction_deadlines
    ADD CONSTRAINT transaction_deadlines_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.transactions(id) ON DELETE CASCADE;


--
-- Name: transaction_deadlines transaction_deadlines_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.transaction_deadlines
    ADD CONSTRAINT transaction_deadlines_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: transactions transactions_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contacts(id) ON DELETE RESTRICT;


--
-- Name: transactions transactions_primary_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_primary_contact_id_fkey FOREIGN KEY (primary_contact_id) REFERENCES public.contacts(id) ON DELETE RESTRICT;


--
-- Name: transactions transactions_secondary_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_secondary_contact_id_fkey FOREIGN KEY (secondary_contact_id) REFERENCES public.contacts(id) ON DELETE SET NULL;


--
-- Name: transactions transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_invites user_invites_invited_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.user_invites
    ADD CONSTRAINT user_invites_invited_by_user_id_fkey FOREIGN KEY (invited_by_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: user_invites user_invites_used_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: dennisfotopoulos
--

ALTER TABLE ONLY public.user_invites
    ADD CONSTRAINT user_invites_used_by_user_id_fkey FOREIGN KEY (used_by_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict t3Ooa8kgWKaJOpbVHTfqLhsBwmVIto3KcJV9PLrwkPYv6pmCAOsgDR9IYBzeyak

