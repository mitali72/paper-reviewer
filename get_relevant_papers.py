import os
import requests
import pandas as pd
import re
from bs4 import BeautifulSoup

class ListPapers():
    
	def __init__(self,query,num_pages):
		self.query = query
		self.num_pages = num_pages

		# creating final repository
		self.paper_repos_dict = {
                    'Paper Title' : [],
                    'Year' : [],
                    'Author' : [],
                    # 'Citation' : [],
                    'Publication' : [],
                    'Url of paper' : [] }
      
	# getting inforamtion of the web page
	def get_paperinfo(self,page_url):

		#download the page
		response=requests.get(page_url)

		# check successful response
		if response.status_code != 200:
			print('Status code:', response.status_code)
			raise Exception('Failed to fetch web page ')

		#parse using beautiful soup
		paper_doc = BeautifulSoup(response.text,'html.parser')

		return paper_doc

	# extracting information of the tags
	def get_tags(self,doc):
		paper_tag = doc.select('[data-lid]')
		cite_tag = doc.select('[title=Cite] + a')
		link_tag = doc.find_all('h3',{"class" : "gs_rt"})
		author_tag = doc.find_all("div", {"class": "gs_a"})

		return paper_tag,cite_tag,link_tag,author_tag

	#return the title of the paper
	def get_papertitle(self,paper_tag):
	
		paper_names = []
		
		for tag in paper_tag:
			paper_names.append(tag.select('h3')[0].get_text())

		return paper_names

	#return the number of citation of the paper
	def get_citecount(self,cite_tag):
		cite_count = []
		# print("len of ", len(cite_tag))
		for i in cite_tag:
			cite = i.text
			print(cite)
			if i is None or cite is None:  # if paper has no citatation then consider 0
				cite_count.append(0)
			else:
				tmp = re.search(r'\d+', cite) #handle the None type object error
				if tmp is None :
					cite_count.append(0)
				else :
					cite_count.append(int(tmp.group()))

		return cite_count
	
	# function for the getting link information
	def get_link(self,link_tag):

		links = []

		for i in range(len(link_tag)) :
			links.append(link_tag[i].a['href']) 

		return links
	
	def get_author_year_publi_info(self,authors_tag):
		years = []
		publication = []
		authors = []
		for i in range(len(authors_tag)):
			authortag_text = (authors_tag[i].text).split()
			year = int(re.search(r'\d+', authors_tag[i].text).group())
			years.append(year)
			publication.append(authortag_text[-1])
			author = authortag_text[0] + ' ' + re.sub(',','', authortag_text[1])
			authors.append(author)
		
		return years , publication, authors
	
	# adding information in repository
	def add_in_paper_repo(self,papername,year,author,publi,link):
		self.paper_repos_dict['Paper Title'].extend(papername)
		self.paper_repos_dict['Year'].extend(year)
		self.paper_repos_dict['Author'].extend(author)
		# self.paper_repos_dict['Citation'].extend(cite)
		self.paper_repos_dict['Publication'].extend(publi)
		self.paper_repos_dict['Url of paper'].extend(link)

		return pd.DataFrame(self.paper_repos_dict)
	

	def get_papers(self):
		for i in range (0,self.num_pages):

			# get url for the each page
			q_plus = '+'.join(self.query.split(" "))
			url = f"https://scholar.google.com/scholar?start={i*10}&q={q_plus}&hl=en&as_sdt=0,5&as_rr=1"

			# function for the get content of each page
			doc = self.get_paperinfo(url)

			# function for the collecting tags
			paper_tag,cite_tag,link_tag,author_tag = self.get_tags(doc)
			
			# paper title from each page
			papername = self.get_papertitle(paper_tag)

			# year , author , publication of the paper
			year , publication , author = self.get_author_year_publi_info(author_tag)

			# cite count of the paper 
			cite = self.get_citecount(cite_tag)

			# url of the paper
			link = self.get_link(link_tag)

			# add in papers in df
			final = self.add_in_paper_repo(papername,year,author,publication,link)
			
			# use sleep to avoid status code 429
			# sleep(30)
		return final

	def download_paper(self,df, indices):

		if not os.path.exists("papers"):
			os.makedirs("./papers")

		for index in indices:
			# try:
			# 	print(df['Url of paper'].iloc[index])
			# 	# wget.download(df['Url of paper'].iloc[index], "user_paper_{index}" + ".pdf")
			# 	urllib.request.urlretrieve(df['Url of paper'].iloc[index],f"user_paper_{index}.pdf")
			# except:
			print(f"Need access to the paper, Pls download manually for review: {df['Url of paper'].iloc[index]}")


if __name__ == "__main__":
    # receive input from user
	user_query = input("Query for papers in area:\n")

    #download papers
	papers = ListPapers(user_query,1)
	print("Top papers")
	paper_list = papers.get_papers()
	print(paper_list[['Paper Title', 'Year','Author','Publication']])

	indices= input(f"Which paperes do you want to review? (Give indices. Eg. 0 1)\n")
	indices = list(map(int,indices.split()))
	papers.download_paper(paper_list,indices)