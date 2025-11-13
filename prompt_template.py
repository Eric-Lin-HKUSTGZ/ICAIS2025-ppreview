"""
Prompt模板 - 用于论文评阅系统的各个阶段
"""


def get_pdf_parse_prompt(pdf_text: str) -> str:
    """PDF结构化解析Prompt"""
    return f"""You are an expert at analyzing academic papers. Your task is to extract structured information from the following PDF text.

Please extract and organize the following information in a structured format:

1. **Title**: The paper title
2. **Authors**: List of authors
3. **Abstract**: The abstract text
4. **Keywords**: Key terms (if available)
5. **Introduction**: Main points from the introduction section
6. **Methodology**: Description of the methods/approach used
7. **Experiments**: Experimental setup and procedures
8. **Results**: Key results and findings
9. **Conclusion**: Main conclusions
10. **References**: List of references (if available)
11. **Paper Type**: Classify as one of: Theoretical, Experimental, Survey/Review, or Other
12. **Core Contributions**: List 3-5 main contributions of this paper
13. **Technical Approach**: Brief description of the technical approach/methodology

PDF Text:
{pdf_text[:20000]}

Please provide the structured information in a clear, organized format. If any section is missing, indicate "Not found"."""


def get_keyword_extraction_prompt(structured_info: str) -> str:
    """关键词提取Prompt"""
    return f"""You are an expert at extracting research keywords. Based on the following structured paper information, extract 3-5 core keywords that best represent this paper's research topic.

These keywords should be:
1. Nouns or noun phrases
2. In lowercase English
3. Representative of the central concepts or approaches
4. Suitable for academic paper search

Structured Paper Information:
{structured_info[:5000]}

Please output exactly 3-5 keywords, separated by commas, without any additional text or formatting.
Example format: keyword1, keyword2, keyword3"""


def get_innovation_analysis_prompt(structured_info: str, related_papers: str) -> str:
    """创新点分析Prompt"""
    return f"""You are an expert at analyzing research innovation. Based on the paper information and related papers, identify the innovation points and differences.

Paper Information:
{structured_info[:5000]}

Related Papers:
{related_papers[:10000]}

Please analyze:
1. **Innovation Points**: What are the novel contributions of this paper?
2. **Differences from Related Work**: How does this paper differ from existing work?
3. **Advantages**: What are the advantages of this paper's approach?
4. **Originality Assessment**: Rate the originality (High/Medium/Low) with brief explanation."""


def get_evaluation_prompt(structured_info: str, innovation_analysis: str, related_papers: str) -> str:
    """多维度评估Prompt"""
    return f"""You are an expert academic reviewer. Please evaluate the following paper from multiple dimensions.

Paper Information:
{structured_info[:5000]}

Innovation Analysis:
{innovation_analysis[:2000]}

Related Papers Context:
{related_papers[:5000]}

Please provide a detailed evaluation covering:

1. **Technical Quality**:
   - Method rationality and soundness
   - Experimental design quality
   - Result credibility and validity
   - Technical rigor

2. **Novelty**:
   - Innovation level
   - Contribution significance
   - Uniqueness compared to existing work

3. **Clarity**:
   - Writing quality
   - Logical flow and organization
   - Presentation clarity
   - Readability

4. **Completeness**:
   - Content completeness
   - Experimental sufficiency
   - Discussion depth
   - Missing elements

Provide detailed analysis for each dimension."""


def get_review_generation_prompt(structured_info: str, evaluation: str, innovation_analysis: str) -> str:
    """评阅报告生成Prompt"""
    return f"""You are an expert academic reviewer. Based on the paper information, evaluation, and innovation analysis, generate a comprehensive review report.

Paper Information:
{structured_info[:5000]}

Evaluation:
{evaluation[:3000]}

Innovation Analysis:
{innovation_analysis[:2000]}

Please generate a review report in Markdown format with the following sections:

# Summary
[Provide a brief summary of the paper and its core contributions]

# Strengths
[List the main strengths and highlights of the paper]

# Weaknesses / Concerns
[Identify weaknesses, concerns, and areas for improvement]

# Questions for Authors
[Pose constructive questions for the authors]

# Score
- Overall: [X]/10
- Novelty: [X]/10
- Technical Quality: [X]/10
- Clarity: [X]/10
- Confidence: [X]/5

Please ensure:
1. The review is constructive and professional
2. Scores are justified by the evaluation
3. Questions are specific and helpful
4. The format matches exactly the structure above"""

