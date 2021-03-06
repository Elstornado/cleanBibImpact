import requests
from habanero import Crossref
import numpy as np
import pandas as pd
import IPython

np.random.seed(seed=93287583)

GENDER_API_KEY = open("gender_api_key.txt", "r").read().strip()


def get_citing_dois(cited_doi):
    """
    Get the dois of papers citing a given doi using opencitations.net

    Silvio Peroni, David Shotton (2020). OpenCitations, an infrastructure
    organization for open scholarship. Quantitative Science Studies, 1(1):
    428-444. https://doi.org/10.1162/qss_a_00023


    Inputs
    ------
    cited_doi : string
        The DOI of the paper whose citing DOIs you want to list.

    Outputs
    -------
    citing_dois : list of strings
        List of DOIs of papers that cite the given DOI.
    """
    url = f"https://opencitations.net/index/coci/api/v1/citations/{cited_doi}"
    items = requests.get(url).json()
    citing_dois = []
    if items:  # if opencitations.net lists citing items
        for item in items:
            citing_dois.append(item["citing"])
    return citing_dois


def get_name_from_author_dict(author_dict):
    """
    This function


    Inputs
    ------
    author_dict : dict
        Dictionary of information about an author, including their given and family names, their place in the sequence of authors (i.e., first, additional, or last), and their affiliation. This is part of the output from a search on Crossref using habanero. E.g.:

        author_dict = {
            "given": "Jane",
            "family": "Doe",
            "sequence": "first",
            "affiliation": [],
        }

    Outputs
    -------
    name : string
        First name of the given author.
    """
    if "given" not in author_dict:
        name = ""
    else:
        # trim initials
        name = author_dict["given"].replace(".", " ").split()[0]
    return name


def names_from_xref(doi):
    """
    Get the first names of the first and last authors for a given DOI.

    Inputs
    ------
    doi : string
        The DOI of the paper whose first and last author names you want to know. Here, it's usually a citing paper.

    Outputs
    -------
    first_author : string
        The first name of the first author of the given paper.

    last_author : string
        The first name of the last author of the given paper.
    """
    cr = Crossref()
    title = ""
    works = cr.works(
        query=title, select=["DOI", "author"], limit=1, filter={"doi": doi}
    )
    if works["message"]["total-results"] > 0:
        item = works["message"]["items"][0]
        if "author" in item.keys():
            first_author = get_name_from_author_dict(item["author"][0])
            last_author = get_name_from_author_dict(item["author"][-1])
        else:
            first_author = ""
            last_author = ""
    return first_author, last_author


def name_to_gender(name, api_key=GENDER_API_KEY):
    """
    This function uses the gender API (https://gender-api.com/) to guess the gender of the given name.

    Note that a major limitation of this code and the original paper is that this is a guess at the gender of a person based only on a first name, and it does not reflect the chosen gender of the author. Further, there are greater limitations if the name is not a traditionally western name. Last, the gender API has limitations in that it doesn't include all types of experienced genders.

    Inputs
    ------
    name : string
        The first name whose gender you want to guess.

    api_key : string
        The API key for the gender API. You can sign up for a free account and get an API key on the gender-api.com website.

    Outputs
    -------
    gender : string
        The guessed gender of the name.

    accuracy : int
        The accuracy of the gender guess, in percent.

    """
    url = f"https://gender-api.com/get?key={api_key}&name={name}"
    response = requests.get(url).json()
    gender = response["gender"]
    accuracy = response["accuracy"]
    return gender, accuracy


def get_data(cited_doi):
    """
    For each doi in a dataframe containing a column called 'doi',get the names, genders, and gender accuracies of the first and last authors.

    Inputs
    ------
    cited_doi: string
        The DOI of the paper whose citing DOIs you want to list.

    Outputs
    -------
    df : pandas DataFrame
        DataFrame with additional columns for the first and last authors' names, guessed genders, and guess accuracies.
    """

    # get the data for the citing papers
    df = pd.DataFrame()

    print("\nLooking for DOIS for the citing papers\n")
    df["doi"] = get_citing_dois(cited_doi=cited_doi)

    print("\nLooking for author names and genders for the citing papers\n")
    if len(df) > 0:  # if there were any citations found
        for n, citing_doi in enumerate(df["doi"]):
            print("\tDOI %d / %d\r" % (n + 1, len(df)), end="")
            fa_name, la_name = names_from_xref(citing_doi)
            fa_gender, fa_accuracy = name_to_gender(fa_name)
            la_gender, la_accuracy = name_to_gender(la_name)

            df.at[n, "first_author_name"] = fa_name
            df.at[n, "first_author_gender"] = fa_gender
            df.at[n, "first_author_gender_accuracy"] = fa_accuracy

            df.at[n, "last_author_name"] = la_name
            df.at[n, "last_author_gender"] = la_gender
            df.at[n, "last_author_gender_accuracy"] = la_accuracy
        print("\n")
    else:
        print("\nNo citations found :( \n")
    return df


# list the cited dois. we're interested in which papers cite these dois
cited_dois = {
    "paper": "10.1038/s41593-020-0658-y",
    "preprint": "10.1101/2020.01.03.894378",
    "code": "10.5281/zenodo.3672109",
}

# for each cited doi, get the citing dois and their name/gender data
citing_papers = pd.DataFrame()
for cited_entity, doi in cited_dois.items():
    print("\n--------------\nLooking for citations of the ", cited_entity)
    df = get_data(cited_doi=doi)
    df["cited_entity"] = cited_entity
    df["cited_doi"] = doi
    citing_papers = citing_papers.append(df)

# save the data as a .csv file
datafile = "../../data/citing_papers.csv"
print(f"\nSaving data to {datafile}\n")
citing_papers.to_csv(datafile)
