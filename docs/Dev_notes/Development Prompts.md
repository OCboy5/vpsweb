Development Prompts

#1
1. Purpose of the vpsweb(Vox Poetica Studio Web) project: 一个专业的翻译和编辑共同协作，用Translator->Editor->Translator的workflow来模拟"初译->编辑意见->完成终稿"的多轮协作诗歌翻译流程，将诗歌在英文和中文（及其它不同语言）之间进行专业翻译，以追求保留原诗的忠实度、诗意、美感、韵律、音乐性和文化贴合度。
2. I want to create a github repository for the project "vpsweb", so all the corresponding developement in this project should follow github project guidelines and structures.
3. I've created a workflow in Dify (the DSL file of the workflow is in the attached file) and it works fine. I would like to convert it into a series of python scripts to perform the same workflow and get the same results. 
4. The python scripts should be highly configurable by config files, including the model definition, prompts of each step, etc.
5. The output of each step of the workflow should be highly structured and can be easily pass to the next step as input.
6. Design the project with the consideration of easily adding a web UI in the future. 
7. Please study the Dify DSL file carefully and ponder on the strategy of converting it into python github project. Create the PSD (Product Specifications Document) first before producing any code.


#2
1. The vpsweb project aims to create a professional, AI-powered poetry translation platform. Its core purpose is to replicate and enhance the “Translator -> Editor -> Translator” (T-E-T) collaborative workflow, producing high-fidelity translations that preserve the original poem's aesthetic beauty, musicality, emotional resonance, and cultural context.
2. I want to create a github repository for the project "vpsweb", so all the corresponding developement in this project should follow github project guidelines and structures.
3. I've created a workflow in Dify (.yml, the DSL file of the workflow is in the attached file) and it works fine. I would like to convert it into a series of python scripts to perform the same workflow and get the same results. 
4. I have collected several PSDs (product specification documents) as attached designed for this project. As an independent senior software architect, please review these documents, select the one version that is most aligned to my project requirements and easiest for Claude Code to implement as the baseline PSD document, integrate into it with ideas or suggestions that are good complements or extensions from the other documents, and produce the final PSD document that will guide the Claude Code implementation later.
5. Generate a step-by-step guide for me to implement this project with the assistance of Claude Code, including appropriate configurations and prompts for Claude Code I should use.

#3
My to do list: v0.1.2
1. convert LLM api call networking protocol from HTTP/1.1 to HTTP/2
2. make sure deepseek api works in this workflow
3. change the final output of 'vpsweb translate' to a markdown text file, including the original poem, the final translation, translation log (initial translation, initial translation notes, editor suggestions, final revision notes)

#4
1.  The vpsweb project aims to create a professional, AI-powered poetry translation platform with broad language selections. Its core purpose is to implement “Translator -> Editor -> Translator” (T-E-T) collaborative workflow, producing human-level or higher high-fidelity translations that preserve the original poem's aesthetic beauty, musicality, emotional resonance, and cultural context.
2. I have included here the 3 prompt templates I used to perform initial translation(initial_translation.yaml), editor review(editor_review.yaml), translator revision(translator_revision.yaml) tasks in the workflow. I also include the LLM model configuration (models.yaml and default.yaml) with model selection and parameters for your reference. These prompt templates are working fine in the current workflow and can produce pretty good translations based on human evaluation.
3. But these prompt templates were developed and tested in older non-reasoning LLM models. Now I'm also using the latest reasoning models. As an expert in both LLM prompt design and poetry translation, I want you to do a thorough study and provide your proposal on how to improve the workflow's translation quality based on the files I provide and your profound knowledge as well as industry best practices. That could include revising the prompt templates according to the model used and adjust the corresponding model parameters for these models. 

4. You should consider 2 sets of prompt templates of the 3 different steps: a. use reasoning model (e.g. Deepseek-v3.2 Exp's deepseek-reasoner) b. use non-reasoning model (e.g. qwen-plus-latest's non-thinking mode). Propose new reasoning mode prompt templates (as the current non-reasoning prompt templates may interfere the COT of reasoning models) and reuse the current non-reasoning prompt templates as much as possible for new non-reasoning prompt templates. The prompt templates should be able to maximize the capability of the underlying reasoning and non-reasoning models. The goal is that I can choose either reasoning or non-reasoning LLM at each step, and even implement mixed model workflows(one reasoning workflow, one non-reasoning workflow and one hybrid workflow(nonreasoning-reasoning-nonreasoning)) as I see appropriate. The model parameters assigned should also reflect to the different models. Use default.yaml to control the selection of different modes in each step.
6. When conducting the study, you should also search and study the official documents from Deepseek, Qwen, OpenAI and others on how to design high quality prompts for reasoning models.
7. The proposal should be in-depth, and representing expert-level standard in both poetry translation and prompt design. The output should be in markdown format and can feed into Claude Code to execute easily.

4. The requirements include: a) consider 2 sets of prompt templates of the 3 different steps: a. use reasoning model (e.g. Deepseek-v3.2 Exp's deepseek-reasoner) b. use non-reasoning model (e.g. qwen-plus-latest's non-thinking mode). Propose new reasoning mode prompt templates (as the current non-reasoning prompt templates may interfere the COT of reasoning models) and reuse the current non-reasoning prompt templates as much as possible for new non-reasoning prompt templates. The prompt templates should be able to maximize the capability of the underlying reasoning and non-reasoning models. b) The goal is that I can choose either reasoning or non-reasoning LLM at each step, and even implement mixed model workflows(one reasoning workflow, one non-reasoning workflow and one hybrid workflow(nonreasoning-reasoning-nonreasoning)) as I see appropriate. c) The model parameters assigned should also align to the different models. d) Use default.yaml to control the selection of different workflow to use.

5. I have include 5 different proposals (.md files) of conducting this enhancement project. Please read and evaluate them thoroughly. Select the one that you regard as the closest to achieve the project goal in terms of quality, completeness and elegance as the baseline document; integrate to the baseline document some of the ideas from the other .md documents that you think are highly relevant and will enhance the quality of the baseline document; reflect and refine the baseline document and turn it into a markdown doc as the project specification document that will be used by claude code to implement the project.  



8. Let me know if you have any questions for me to clarify before you start the study or during the study. 


#5 wechat article auto gen&pub
1. Next phase of the vpsweb project, I would like to add 2 new functions to convert the output of vpsweb translate workflow to a Wechat article(微信公众号文章) and publish it automatically.
2. I would like to introduce 2 new cli commands for this purpose:
   a) vpsweb generate-article
    From the output of .json file from previous vpsweb translate, generate a Wechat article with a title of "【知韵译诗】诗歌名（诗人名）“，content includes the original poem, the final translation, and a brief "translation notes" to summarize the main translation decisions forming the final translation by info extracting from the outputs/.json log file. 
    The format of the article should be professional, easy to read, and with elegant design. It should also include appropriate copyright disclaimer at the end of the article.  
   b) vpsweb publish-article
   Publish the generated article by vpsweb generate-article to my personal 微信公众号 account's Draft folder(草稿), which I can review and publish manually later. I plan to publish 1 articale per day. 
3. I would like to have the capability to assign a cover image stared locally for the Wechat article 
4. We should create the "translation notes" for the Wechat article in the vpsweb generate-article workflow.
5. Please refer to the sample JSON output file above as you design your strategy. Please think about if we should add more metadata in the vpsweb translate workflow.
6. If you are not familiar with 微信公众号 and its development best practices，please do your research first.
7. Please think very hard to create your proposal. The proposal should be a further expansion on what we have done in the vpsweb project.    

#6 poem translation repository
1. Can you access https://github.com/OCboy5/vpsweb ? It can now work as an AI-driven poetry translation production system.
1. Here are some reference docs from vpsweb (README.md and 3 output files).
2. Next step, I want to create a central poetry translation repository for vpsweb to enable easy classification, access and searching for the translated poems (eventually hundreds or even thousands poems), and potentially build a Web UI for the TET workflow as well as accessing the repository. I would also need a Web UI to input and store some poem translations by human translators in the repository, so the users can compare human and AI translation in the future.
3. Please think hard about this idea, evaluate different approaches(techiniques, tools, etc.), and generate a draft strategy. The project is still in development mode, so we can change the storage structure, metadata, naming schemes, etc. freely if we regard necessary. For now, I expect the final production system to be a low network volume niche website.
4. I agree with your proposal. can you convert it into a project specification document (PSD) in markdown format that I can later feed into claude code for it to implement?



## Blueprint

2. develop a poem translation collection archive with interface, metadata
3. develop a tts UI for the translated poems
4. develop a Web UI and a xiaochengxu UI
5.

think hard
ultrathink

CC:
#1 now let's move on to the next stage of the project: fine tune the LLM prompt templates by introducing 3 different workflows (reasoning, non-reasoning, hybrid). Pleasa read the proposal at docs/PSD-reasoning-CC.md, understand and evaluate the pros and cons of the enhancement proposal, define your own strategy to implement this. 



