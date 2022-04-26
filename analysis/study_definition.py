################################################################################
#
# Description: This script provides the formal specification of the study data 
#              that will be extracted from the OpenSAFELY database.
#
# Output: output/data/input.feather
#
# Author(s): M Green, H Curtis
#
################################################################################


# IMPORT STATEMENTS ----

## Import code building blocks from cohort extractor package
from cohortextractor import (
  StudyDefinition,
  patients,
  codelist,
  combine_codelists,
)

## Import codelists from codelist.py (which pulls them from the codelist folder)
from codelists import *
  
  
# DEFINE STUDY POPULATION ----

## Define study time variables
campaign_start = "2021-12-16"


## Define study population and variables
study = StudyDefinition(
  
  # PRELIMINARIES ----
  
  ## Configure the expectations framework
  default_expectations = {
    "date": {"earliest": "2021-11-01", "latest": "today"},
    "rate": "uniform",
    "incidence": 0.05,
  },
  
  ## Define index date
  index_date = campaign_start,
  
  # POPULATION ----
  ## aged 12-110 and registered at time of outpatient MABs/antiviral treatment
  population = patients.satisfying(
    """
    age_group != "missing"
    AND (registered_op OR registered_ip)
    """,
  ),
  
  
  
  # OUTPATIENT TREATMENT (BlueTeq) - NEUTRALISING MONOCLONAL ANTIBODIES OR ANTIVIRALS ----

  # date of first outpatient treatment
  outpatient_covid_therapeutic_date = patients.with_covid_therapeutics(
    #with_these_statuses = ["Approved", "Treatment Complete"],
    with_these_indications = "non_hospitalised",
    on_or_after = "index_date",
    find_first_match_in_period = True,
    returning = "date",
    date_format = "YYYY-MM-DD",
    return_expectations = {
      "date": {"earliest": "index_date"},
      "incidence": 0.8
    },
  ), 
  
  # name of first outpatient treatment
  outpatient_covid_therapeutic_name = patients.with_covid_therapeutics(
    #with_these_statuses = ["Approved", "Treatment Complete"],
    with_these_indications = "non_hospitalised",
    on_or_after = "index_date",
    find_first_match_in_period = True,
    returning = "therapeutic",
    return_expectations = {
      "category":{
        "ratios": {'remdesivir':0.1, 
                   'casirivimab and imdevimab':0.1, 
                   'molnupiravir':0.3, 
                   'sotrovimab': 0.3, 
                   'paxlovid': 0.2},
              },
      "incidence": 0.8
    },
  ), 
  
  
  ### INPATIENT COVID TREATMENT (BlueTeq)
  # available from July 2020 

  # date of first inpatient treatment
  inpatient_covid_therapeutic_date = patients.with_covid_therapeutics(
    with_these_indications = ["hospitalised_with", "hospital_onset"],
    on_or_after = "index_date",
    find_first_match_in_period = True,
    returning = "date",
    date_format = "YYYY-MM-DD",
    return_expectations = {
      "date": {"earliest": "index_date"},
      "incidence": 0.8
    },
  ), 
  
  # name of first inpatient treatment
  inpatient_covid_therapeutic_name = patients.with_covid_therapeutics(
    with_these_indications = ["hospitalised_with", "hospital_onset"],
    on_or_after = "index_date",
    find_first_match_in_period = True,
    returning = "therapeutic",
    return_expectations = {
      "category":{
        "ratios": {'remdesivir':0.3, 
                   'casirivimab and imdevimab':0.05, 
                   'molnupiravir':0.15, 
                   'sotrovimab': 0.2, 
                   'paxlovid': 0.1,
                   'tocilizumab': 0.1,
                   'sarilumab':0.1},
              },
      "incidence": 0.8
    },
  ), 
  
  registered_op = patients.registered_as_of("outpatient_covid_therapeutic_date"),
  registered_ip = patients.registered_as_of("inpatient_covid_therapeutic_date"),
  

  ############################
  ## Treated in hospital SUS data near time of recorded treatment
    ## NB this data lags behind the therapeutics/testing data so may be missing

  ### Any elective admission with COVID as primary diagnosis (with or without a recorded procedure)
  elective_admission_date = patients.admitted_to_hospital(
    returning = "date_admitted",
    with_these_primary_diagnoses = covid_icd10_codes,
    with_patient_classification = ["1", "2"], # ordinary or day case admissions only
    with_admission_method = ['11', '12', '13', '81'], ## elective (inc transfer)
    # see https://docs.opensafely.org/study-def-variables/#sus for more info
    between = ["outpatient_covid_therapeutic_date - 3 days", "outpatient_covid_therapeutic_date + 3 days"],
    date_format = "YYYY-MM-DD",
    find_first_match_in_period = True,
    return_expectations = {
      "date": {"earliest": "index_date"},
      "rate": "uniform",
      "incidence": 0.05
    },
  ),

  # short stay elective (1-2 days)
  elective_short_stay = patients.satisfying(
    "elective_bed_days < 3",
    # bed days (closest approximation of length of spell)
    elective_bed_days = patients.admitted_to_hospital(
      returning = "total_bed_days_in_period",
      with_these_primary_diagnoses = covid_icd10_codes,
      with_patient_classification = ["1", "2"], # ordinary or day case admissions only
      with_admission_method = ['11', '12', '13', '81'], ## elective (inc transfer)
      # see https://docs.opensafely.org/study-def-variables/#sus for more info
      between = ["elective_admission_date", "elective_admission_date + 3 days"],
    ),
    return_expectations = {
      "incidence": 0.7
    }
  ),

  ### Day case admission with COVID as primary diagnosis (with or without a recorded procedure)
  daycase_admission_date = patients.admitted_to_hospital(
    returning = "date_admitted",
    with_these_primary_diagnoses = covid_icd10_codes,
    with_patient_classification = ["2"], # ordinary or day case admissions only
    with_admission_method = ['11', '12', '13', '81'], ## elective (inc transfer)
    # see https://docs.opensafely.org/study-def-variables/#sus for more info
    between = ["outpatient_covid_therapeutic_date - 3 days", "outpatient_covid_therapeutic_date + 3 days"],
    date_format = "YYYY-MM-DD",
    find_first_match_in_period = True,
    return_expectations = {
      "date": {"earliest": "index_date"},
      "rate": "uniform",
      "incidence": 0.5
    },
  ),

  ### Treated with molnupiravir - procedure 'X748'
  # none found in preliminary investigation
  

  ### Elective admission with procedure:
  ###  'X892' Monoclonal antibodies band 2 (used for ronapreve)
  elective_x892_date = patients.admitted_to_hospital(
    returning = "date_admitted",
    with_these_primary_diagnoses = covid_icd10_codes,
    with_these_procedures = codelist(['X892'], system='opcs4'),
    with_patient_classification = ["1", "2"], # ordinary or day case admissions only
    with_admission_method = ['11', '12', '13', '81'], ## elective (inc transfer)
    # see https://docs.opensafely.org/study-def-variables/#sus for more info
    between = ["outpatient_covid_therapeutic_date - 3 days", "outpatient_covid_therapeutic_date + 3 days"],
    date_format = "YYYY-MM-DD",
    find_first_match_in_period = True,
    return_expectations = {
      "date": {"earliest": "index_date"},
      "rate": "uniform",
      "incidence": 0.1
    },
  ),
  
  ### Elective admission With procedure: 
  ### 'X292' continuous infusion of therapeutic substance
  elective_x292_date = patients.admitted_to_hospital(
    returning = "date_admitted",
    with_these_primary_diagnoses = covid_icd10_codes,
    with_these_procedures = codelist(['X292'], system='opcs4'),
    with_patient_classification = ["1", "2"], # ordinary or day case admissions only
    with_admission_method = ['11', '12', '13', '81'], ## elective (inc transfer)
    # see https://docs.opensafely.org/study-def-variables/#sus for more info
    between = ["outpatient_covid_therapeutic_date - 3 days", "outpatient_covid_therapeutic_date + 3 days"],
    date_format = "YYYY-MM-DD",
    find_first_match_in_period = True,
    return_expectations = {
      "date": {"earliest": "index_date"},
      "rate": "uniform",
      "incidence": 0.1
    },
  ),
  


  ## Hospital outpatient appointment (SUS)

  ## NB this data lags behind the therapeutics/testing data so need to filter in next step
  # diagnoses are rarely coded in outpatient data
  hospital_attendance_date = patients.outpatient_appointment_date(
    returning = "date",
    with_these_procedures = codelist(['X892','X292'], system='opcs4'),
    between = ["outpatient_covid_therapeutic_date - 3 days", "outpatient_covid_therapeutic_date + 3 days"],
    date_format = "YYYY-MM-DD",
    find_first_match_in_period = True,
    return_expectations = {
      "date": {"earliest": "index_date"},
      "rate": "uniform",
      "incidence": 0.1
    },
  ),

  #  sus or op
  elective_or_op = patients.satisfying(
    '''elective_short_stay OR
    hospital_attendance_date ''',
    return_expectations = {
      "incidence": 0.8
    },
  ),


  ### To match with Blueteq INPATIENT treatment
  ### Any admission (SUS) (include elective in case of hospital-onset COVID) Without procedure: 
  any_admission_date = patients.admitted_to_hospital(
    returning = "date_admitted",
    with_these_diagnoses = covid_icd10_codes,
    with_patient_classification = ["1"], # ordinary admissions only
    # see https://docs.opensafely.org/study-def-variables/#sus for more info
    on_or_before = "inpatient_covid_therapeutic_date",
    date_format = "YYYY-MM-DD",
    find_first_match_in_period = True,
    return_expectations = {
      "date": {"earliest": "index_date"},
      "rate": "uniform",
      "incidence": 0.5
    },
  ),
  
  ### [Discharge date] Any admission (SUS) without procedure: 
  any_discharge_date = patients.admitted_to_hospital(
    returning = "date_discharged",
    with_these_diagnoses = covid_icd10_codes,
    with_patient_classification = ["1"], # ordinary admissions only
    # see https://docs.opensafely.org/study-def-variables/#sus for more info
    between = ["any_admission_date","any_admission_date"],
    date_format = "YYYY-MM-DD",
    find_first_match_in_period = True,
    return_expectations = {
      "date": {"earliest": "index_date"},
      "rate": "uniform",
      "incidence": 0.5
    },
  ),
  ### Admission (SUS) With procedure: 
  ### 'X892' Monoclonal antibodies band 2 (used for ronapreve)
  any_admission_x892_date = patients.admitted_to_hospital(
    returning = "date_admitted",
    with_these_diagnoses = covid_icd10_codes,
    with_these_procedures = codelist(['X292'], system='opcs4'),
    with_patient_classification = ["1"], # ordinary admissions only
    # see https://docs.opensafely.org/study-def-variables/#sus for more info
    on_or_before = "inpatient_covid_therapeutic_date",
    date_format = "YYYY-MM-DD",
    find_first_match_in_period = True,
    return_expectations = {
      "date": {"earliest": "index_date"},
      "rate": "uniform",
      "incidence": 0.3
    },
  ),
  
  ### [Discharge date] Admission (SUS) With procedure: 
  ### 'X892' Monoclonal antibodies band 2 (used for ronapreve)
  any_discharge_x892_date = patients.admitted_to_hospital(
    returning = "date_discharged",
    with_these_diagnoses = covid_icd10_codes,
    with_these_procedures = codelist(['X292'], system='opcs4'),
    with_patient_classification = ["1"], # ordinary admissions only
    # see https://docs.opensafely.org/study-def-variables/#sus for more info
    between = ["any_admission_x892_date","any_admission_x892_date"],
    date_format = "YYYY-MM-DD",
    find_first_match_in_period = True,
    return_expectations = {
      "date": {"earliest": "index_date"},
      "rate": "uniform",
      "incidence": 0.3
    },
  ),


    ### Admission (SUS) With procedure: 
  ### 'X292' continuous infusion of therapeutic substance
  any_admission_x292_date = patients.admitted_to_hospital(
    returning = "date_admitted",
    with_these_diagnoses = covid_icd10_codes,
    with_these_procedures = codelist(['X292'], system='opcs4'),
    with_patient_classification = ["1"], # ordinary admissions only
    # see https://docs.opensafely.org/study-def-variables/#sus for more info
    on_or_before = "inpatient_covid_therapeutic_date",
    date_format = "YYYY-MM-DD",
    find_first_match_in_period = True,
    return_expectations = {
      "date": {"earliest": "index_date"},
      "rate": "uniform",
      "incidence": 0.3
    },
  ),
  
  ### [Discharge date] Admission (SUS) With procedure: 
  ### 'X292' continuous infusion of therapeutic substance
  any_discharge_x292_date = patients.admitted_to_hospital(
    returning = "date_discharged",
    with_these_diagnoses = covid_icd10_codes,
    with_these_procedures = codelist(['X292'], system='opcs4'),
    with_patient_classification = ["1"], # ordinary admissions only
    # see https://docs.opensafely.org/study-def-variables/#sus for more info
    between = ["any_admission_x292_date","any_admission_x292_date"],
    date_format = "YYYY-MM-DD",
    find_first_match_in_period = True,
    return_expectations = {
      "date": {"earliest": "index_date"},
      "rate": "uniform",
      "incidence": 0.3
    },
  ),

  ## Study start date for extracting variables  
  start_date = patients.minimum_of(
    "outpatient_covid_therapeutic_date",
    "inpatient_covid_therapeutic_date"
  ),



  
 
  ## Blueteq ‘high risk’ cohort 
  ## only present for 3 drugs currently
  high_risk_cohort_covid_therapeutics = patients.with_covid_therapeutics(
    #with_these_indications = "non_hospitalised", 
    on_or_after = "index_date",
    find_first_match_in_period = True,
    returning = "risk_group",
    return_expectations = {
      "rate": "universal",
      "incidence": 0.4,
      "category": {
        "ratios": {
          "Downs syndrome": 0.1,
          "sickle cell disease": 0.1,
          "solid cancer": 0.1,
          "haematological diseases,stem cell transplant recipients": 0.1,
          "renal disease,sickle cell disease": 0.1,
          "liver disease": 0.05,
          "IMID": 0.1,
          "IMID,solid cancer": 0.1,
          "haematological malignancies": 0.05,
          "primary immune deficiencies": 0.1,
          "HIV or AIDS": 0.05,
          "NA":0.05,},},
    },
  ),
  
  
  # KEY DEMOGRAPHIC COVARIATES ----
  
  ## Age
  age_group = patients.categorised_as({
        "12-24": "age >= 12 AND age < 25",
        "25-34": "age >= 25 AND age < 35",
        "35-44": "age >= 35 AND age < 45",
        "45-54": "age >= 45 AND age < 55",
        "55-64": "age >= 55 AND age < 65",
        "65-74": "age >= 65 AND age < 75",
        "75+":   "age >= 75 AND age < 110",
        "missing": "DEFAULT",
    },
    return_expectations = {
        "rate": "universal",
        "category": {
            "ratios": {
                "12-24": 0.1,
                "25-34": 0.1,
                "35-44": 0.2,
                "45-54": 0.2,
                "55-64": 0.1,
                "65-74": 0.1,
                "75+": 0.1,
                "missing": 0.1,
            }
        },
    },
    age = patients.age_as_of(
      "start_date",
    )
  ),
  
  ## Sex
  sex = patients.sex(
    return_expectations = {
      "rate": "universal",
      "category": {"ratios": {"M": 0.49, "F": 0.51}},
    }
  ),
  
#   ## Ethnicity
#   ethnicity = patients.categorised_as({
#         "0": "DEFAULT",
#         "1": "eth='1' OR (NOT eth AND ethnicity_sus='1')",
#         "2": "eth='2' OR (NOT eth AND ethnicity_sus='2')",
#         "3": "eth='3' OR (NOT eth AND ethnicity_sus='3')",
#         "4": "eth='4' OR (NOT eth AND ethnicity_sus='4')",
#         "5": "eth='5' OR (NOT eth AND ethnicity_sus='5')",
#     },
#     return_expectations={
#         "category": {
#             "ratios": {
#                 "1": 0.2,
#                 "2": 0.2,
#                 "3": 0.2,
#                 "4": 0.2,
#                 "5": 0.2
#                 }
#             },
#         "incidence": 0.8,
#       },
#     eth = patients.with_these_clinical_events(
#       ethnicity_primis_snomed_codes,
#       returning = "category",
#       on_or_before = "start_date",
#       find_first_match_in_period = True,
#       include_date_of_match = False,
#     ),
#     ethnicity_sus = patients.with_ethnicity_from_sus(
#       returning = "group_6",  
#       use_most_frequent_code = True,
#     ),
#   ),
  
  ## Index of multiple deprivation
  imd = patients.categorised_as(
    {"0": "DEFAULT",
      "1": """index_of_multiple_deprivation >=1 AND index_of_multiple_deprivation < 32844*1/5""",
      "2": """index_of_multiple_deprivation >= 32844*1/5 AND index_of_multiple_deprivation < 32844*2/5""",
      "3": """index_of_multiple_deprivation >= 32844*2/5 AND index_of_multiple_deprivation < 32844*3/5""",
      "4": """index_of_multiple_deprivation >= 32844*3/5 AND index_of_multiple_deprivation < 32844*4/5""",
      "5": """index_of_multiple_deprivation >= 32844*4/5 """,
    },
    index_of_multiple_deprivation = patients.address_as_of(
      "start_date",
      returning = "index_of_multiple_deprivation",
      round_to_nearest = 100,
    ),
    return_expectations = {
      "rate": "universal",
      "category": {
        "ratios": {
          "0": 0.01,
          "1": 0.20,
          "2": 0.20,
          "3": 0.20,
          "4": 0.20,
          "5": 0.19,
        }},
    },
  ),
  
  ## Region - NHS England 9 regions
  region_nhs = patients.registered_practice_as_of(
    "start_date",
    returning = "nuts1_region_name",
    return_expectations = {
      "rate": "universal",
      "category": {
        "ratios": {
          "North East": 0.1,
          "North West": 0.1,
          "Yorkshire and The Humber": 0.1,
          "East Midlands": 0.1,
          "West Midlands": 0.1,
          "East": 0.1,
          "London": 0.2,
          "South West": 0.1,
          "South East": 0.1,},},
    },
  ),
  
  region_covid_therapeutics = patients.with_covid_therapeutics(
    with_these_indications = "non_hospitalised",
    on_or_after = "start_date",
    find_first_match_in_period = True,
    returning = "region",
    return_expectations = {
      "rate": "universal",
      "category": {
        "ratios": {
          "North East": 0.1,
          "North West": 0.1,
          "Yorkshire and The Humber": 0.1,
          "East Midlands": 0.1,
          "West Midlands": 0.1,
          "East": 0.1,
          "London": 0.2,
          "South West": 0.1,
          "South East": 0.1,},},
    },
  ),
  
  # STP (NHS administration region based on geography, currenty closest match to CMDU)
  stp = patients.registered_practice_as_of(
    "start_date",
    returning = "stp_code",
    return_expectations = {
      "rate": "universal",
      "category": {
        "ratios": {
          "STP1": 0.1,
          "STP2": 0.1,
          "STP3": 0.1,
          "STP4": 0.1,
          "STP5": 0.1,
          "STP6": 0.1,
          "STP7": 0.1,
          "STP8": 0.1,
          "STP9": 0.1,
          "STP10": 0.1,
        }
      },
    },
  ),
  
  # Rurality
  rural_urban = patients.address_as_of(
    "start_date",
    returning = "rural_urban_classification",
    return_expectations = {
      "rate": "universal",
      "category": {"ratios": {1: 0.125, 2: 0.125, 3: 0.125, 4: 0.125, 5: 0.125, 6: 0.125, 7: 0.125, 8: 0.125}},
      "incidence": 1,
    },
  ),
  
  
  
  # CLINICAL GROUPS ----
  
#   ## Care home 
#   care_home_primis = patients.with_these_clinical_events(
#     care_home_primis_snomed_codes,
#     returning = "binary_flag",
#     on_or_before = "start_date",
#     return_expectations = {"incidence": 0.15,}
#   ),
  
#   ## Housebound
#   housebound_opensafely = patients.satisfying(
#     """housebound_date
#                 AND NOT no_longer_housebound
#                 AND NOT moved_into_care_home""",
#     return_expectations={
#       "incidence": 0.01,
#     },
    
#     housebound_date = patients.with_these_clinical_events( 
#       housebound_opensafely_snomed_codes, 
#       on_or_before = "start_date",
#       find_last_match_in_period = True,
#       returning = "date",
#       date_format = "YYYY-MM-DD",
#     ),   
    
#     no_longer_housebound = patients.with_these_clinical_events( 
#       no_longer_housebound_opensafely_snomed_codes, 
#       on_or_after = "housebound_date",
#     ),
    
#     moved_into_care_home = patients.with_these_clinical_events(
#       care_home_primis_snomed_codes,
#       on_or_after = "housebound_date",
#     ),
    
#   ),
  
  
)
