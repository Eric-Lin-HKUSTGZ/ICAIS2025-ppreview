"""
Prompt模板 V2 - 基于大模型能力的论文评阅系统（不涉及文件检索）
高质量、详细的 prompt 设计，确保模型输出准确无误的评阅结果
"""
import re


def detect_language(text: str) -> str:
    """检测文本语言，返回'zh'（中文）或'en'（英文）"""
    if not text:
        return 'en'
    
    # 统计中文字符数量
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 统计总字符数量（排除空格和标点）
    total_chars = len(re.findall(r'[a-zA-Z\u4e00-\u9fff]', text))
    
    if total_chars == 0:
        return 'en'
    
    # 如果中文字符占比超过30%，认为是中文
    if chinese_chars / total_chars > 0.3:
        return 'zh'
    else:
        return 'en'


def get_pdf_parse_prompt(pdf_text: str, language: str = 'en') -> str:
    """PDF结构化解析Prompt（V1和V2共用）"""
    if language == 'zh':
        prompt = f"""你是一位学术论文分析专家。你的任务是从以下PDF文本中提取结构化信息。

请提取并组织以下信息为结构化格式：

1. **Title（标题）**: 论文标题
2. **Authors（作者）**: 作者列表
3. **Abstract（摘要）**: 摘要文本
4. **Keywords（关键词）**: 关键词（如果有）
5. **Introduction（引言）**: 引言部分的主要观点
6. **Methodology（方法论）**: 使用的方法/方法描述
7. **Experiments（实验）**: 实验设置和程序
8. **Results（结果）**: 主要结果和发现
9. **Conclusion（结论）**: 主要结论
10. **References（参考文献）**: 参考文献列表（如果有）
11. **Paper Type（论文类型）**: 分类为以下之一：理论性、实验性、综述/评论或其他
12. **Core Contributions（核心贡献）**: 列出本文的3-5个主要贡献
13. **Technical Approach（技术方法）**: 技术方法/方法论的简要描述

PDF文本：
{pdf_text[:20000]}

请严格按照以下格式输出，每个字段使用以下格式之一：
- "Abstract: 内容" 或 "**Abstract**: 内容"
- "摘要: 内容" 或 "**摘要**: 内容"

重要格式要求：
1. 每个字段名称后必须紧跟冒号（:或：）
2. 字段名称可以使用英文（如Abstract）或中文（如摘要）
3. 可以使用Markdown加粗格式（**字段名**）
4. 如果使用编号格式（1. 2. 3.），请确保字段名称和冒号在同一行

请以清晰、有组织的形式提供结构化信息。如果任何部分缺失，请注明"未找到"。

请使用中文回答。所有输出内容都必须是中文。"""
    else:
        prompt = f"""You are an expert at analyzing academic papers. Your task is to extract structured information from the following PDF text.

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

Please strictly follow the following format for each field:
- "Abstract: content" or "**Abstract**: content"

Important format requirements:
1. Each field name must be followed immediately by a colon (:)
2. Field names can be in English (e.g., Abstract, Introduction)
3. Markdown bold format (**Field Name**) is allowed
4. If using numbered format (1. 2. 3.), ensure the field name and colon are on the same line

Please provide the structured information in a clear, organized format. If any section is missing, indicate "Not found"."""
    
    return prompt


def get_innovation_analysis_prompt_v2(structured_info: str, language: str = 'en') -> str:
    """
    创新点分析Prompt V2 - 基于论文内容本身进行深度分析
    不依赖外部论文检索，完全基于论文自身内容识别创新点
    """
    if language == 'zh':
        prompt = f"""你是一位资深的研究创新分析专家，具有深厚的学术背景和敏锐的创新洞察力。你的任务是基于论文内容本身，深入分析论文的创新点和贡献。

**重要原则**：
1. **基于论文内容**：所有分析必须严格基于提供的论文信息，不得编造或推测论文中未提及的内容
2. **引用具体位置**：如果论文信息中包含章节号、图表号（如§3.2、Figure 1、Table 2等），请在分析中引用这些具体位置
3. **深度理解**：深入理解论文的技术路线、方法设计和实验设计，识别真正的创新点
4. **客观准确**：保持客观，准确区分论文的创新点和已有技术的应用

论文结构化信息：
{structured_info[:8000]}

请从以下维度进行深入分析：

## 1. 核心创新点识别（Core Innovation Points）

请识别论文的3-5个核心创新点，每个创新点需要：
- **明确描述**：用1-2句话清晰描述该创新点是什么
- **技术细节**：说明该创新点的技术实现方式或设计思路
- **引用位置**：如果可能，引用论文中的具体章节、图表或表格（如"在§3.2中提出的..."、"如图2所示..."）
- **创新程度**：评估该创新点的创新程度（突破性创新/重要改进/渐进式改进）

## 2. 技术贡献分析（Technical Contributions）

请分析论文在技术层面的具体贡献：
- **方法创新**：论文提出了哪些新的方法、算法或技术路线？
- **理论贡献**：是否有理论分析、证明或新的理论框架？
- **工程贡献**：是否有新的系统设计、架构或实现方式？
- **应用创新**：是否有新的应用场景或问题定义？

对于每个贡献，请：
- 详细说明其技术内容
- 解释为什么这是一个贡献（解决了什么问题）
- 引用论文中的具体证据（章节、图表、数据等）

## 3. 与现有技术的区别（Differences from Existing Approaches）

基于论文中提到的相关工作（Related Work）部分，分析：
- **方法差异**：论文方法与现有方法在技术路线上的本质区别
- **优势分析**：论文方法相比现有方法的优势（性能、效率、适用性等）
- **局限性说明**：论文方法相比现有方法的局限性或适用场景限制

**注意**：如果论文中没有明确提到相关工作，请基于论文内容本身推断其可能的创新之处，但必须明确说明这是基于论文内容的推断。

## 4. 原创性评估（Originality Assessment）

请从以下角度评估论文的原创性：
- **新颖性**：论文提出的方法、概念或技术是否新颖？
- **独立性**：论文的工作是否独立完成，还是主要基于已有工作的改进？
- **深度**：论文的创新是否有足够的深度，还是只是表面的改进？
- **影响**：论文的创新对领域可能产生的影响

请给出原创性评级（高/中/低）并详细说明理由。

## 5. 技术优势与局限性（Advantages and Limitations）

请分析：
- **技术优势**：论文方法在哪些方面具有优势（性能、效率、可扩展性、适用性等）？请引用具体的实验数据或分析结果
- **技术局限性**：论文方法在哪些方面存在局限性？请基于论文内容本身进行分析，不要编造

**输出要求**：
1. 所有分析必须基于提供的论文信息，不得编造
2. 尽可能引用论文中的具体章节、图表、表格或数据
3. 保持客观、准确、深入
4. 使用清晰的结构和逻辑组织内容
5. 如果某些信息在论文中缺失，请明确说明

请使用中文回答。所有输出内容都必须是中文。"""
    else:
        prompt = f"""You are a senior research innovation analysis expert with deep academic background and keen insight into innovation. Your task is to deeply analyze the innovation points and contributions of the paper based solely on the paper content itself.

**Key Principles**:
1. **Based on paper content**: All analysis must strictly be based on the provided paper information. Do not fabricate or speculate about content not mentioned in the paper.
2. **Cite specific locations**: If the paper information includes section numbers, figure/table numbers (e.g., §3.2, Figure 1, Table 2), please cite these specific locations in your analysis.
3. **Deep understanding**: Deeply understand the paper's technical approach, method design, and experimental design to identify true innovation points.
4. **Objective and accurate**: Maintain objectivity and accurately distinguish between the paper's innovations and applications of existing techniques.

Structured Paper Information:
{structured_info[:8000]}

Please conduct in-depth analysis from the following dimensions:

## 1. Core Innovation Points Identification

Please identify 3-5 core innovation points of the paper. For each innovation point, provide:
- **Clear description**: Use 1-2 sentences to clearly describe what this innovation is.
- **Technical details**: Explain the technical implementation or design approach of this innovation.
- **Citation**: If possible, cite specific sections, figures, or tables in the paper (e.g., "as proposed in §3.2...", "as shown in Figure 2...").
- **Innovation level**: Assess the innovation level (breakthrough innovation/important improvement/incremental improvement).

## 2. Technical Contributions Analysis

Please analyze the paper's specific technical contributions:
- **Method innovation**: What new methods, algorithms, or technical approaches does the paper propose?
- **Theoretical contribution**: Are there theoretical analyses, proofs, or new theoretical frameworks?
- **Engineering contribution**: Are there new system designs, architectures, or implementation approaches?
- **Application innovation**: Are there new application scenarios or problem definitions?

For each contribution, please:
- Detail its technical content
- Explain why this is a contribution (what problem does it solve)
- Cite specific evidence from the paper (sections, figures, data, etc.)

## 3. Differences from Existing Approaches

Based on the related work section mentioned in the paper, analyze:
- **Method differences**: Essential differences between the paper's method and existing methods in technical approach.
- **Advantage analysis**: Advantages of the paper's method compared to existing methods (performance, efficiency, applicability, etc.).
- **Limitation explanation**: Limitations or applicable scenario restrictions of the paper's method compared to existing methods.

**Note**: If the paper does not explicitly mention related work, please infer possible innovations based on the paper content itself, but must clearly state that this is an inference based on the paper content.

## 4. Originality Assessment

Please assess the paper's originality from the following perspectives:
- **Novelty**: Are the methods, concepts, or techniques proposed in the paper novel?
- **Independence**: Is the paper's work independently completed, or is it mainly an improvement based on existing work?
- **Depth**: Does the paper's innovation have sufficient depth, or is it just a superficial improvement?
- **Impact**: Potential impact of the paper's innovation on the field.

Please provide an originality rating (High/Medium/Low) with detailed justification.

## 5. Technical Advantages and Limitations

Please analyze:
- **Technical advantages**: In which aspects does the paper's method have advantages (performance, efficiency, scalability, applicability, etc.)? Please cite specific experimental data or analysis results.
- **Technical limitations**: In which aspects does the paper's method have limitations? Please analyze based on the paper content itself, do not fabricate.

**Output Requirements**:
1. All analysis must be based on the provided paper information, do not fabricate.
2. Cite specific sections, figures, tables, or data from the paper whenever possible.
3. Maintain objectivity, accuracy, and depth.
4. Use clear structure and logical organization.
5. If certain information is missing in the paper, please clearly state this.

Please provide your analysis in English."""
    
    return prompt


def get_evaluation_prompt_v2(structured_info: str, innovation_analysis: str, language: str = 'en') -> str:
    """
    多维度评估Prompt V2 - 基于论文内容本身进行深度评估
    不依赖外部论文检索，完全基于论文自身内容进行评估
    """
    if language == 'zh':
        prompt = f"""你是一位资深的学术评阅专家，具有丰富的论文评阅经验和深厚的学术背景。请基于论文内容本身，从多个维度深入评估以下论文。

**重要原则**：
1. **基于论文内容**：所有评估必须严格基于提供的论文信息，不得编造或推测论文中未提及的内容
2. **引用具体位置**：如果论文信息中包含章节号、图表号（如§3.3.1、Table 3、Figure 2等），请在评估中引用这些具体位置
3. **证据支撑**：所有评估结论必须有具体的证据支撑，引用论文中的具体内容、数据或结果
4. **客观深入**：保持客观、建设性的评估态度，深入分析论文的各个方面

论文结构化信息：
{structured_info[:8000]}

创新点分析：
{innovation_analysis[:3000]}

请从以下维度进行详细评估，**每个维度都必须提供深入、具体的分析，避免泛泛而谈**：

## 1. 技术质量（Technical Quality）

请从以下方面评估论文的技术质量：

### 1.1 方法的合理性和可靠性
- **理论基础**：评估方法设计的理论基础是否扎实？是否有充分的理论支撑？
- **技术路线**：评估技术路线的合理性，方法设计是否逻辑清晰、步骤明确？
- **算法设计**：评估算法设计的合理性，是否有清晰的算法描述和伪代码？
- **实现细节**：论文是否提供了足够的实现细节？是否便于复现？

**要求**：请引用论文中的具体章节、公式或算法描述来支撑你的评估。

### 1.2 实验设计质量
- **实验设置**：评估实验设置的严谨性，包括数据集选择、评估指标、实验环境等
- **对照实验**：评估对照组的合理性，是否与相关方法进行了公平比较？
- **评估指标**：评估评估指标的恰当性，是否全面、合理？
- **实验规模**：评估实验的规模和充分性，是否足够验证论文的贡献？

**要求**：请引用论文中的具体实验设置、数据集信息或实验结果来支撑你的评估。

### 1.3 结果的可信度和有效性
请深入分析实验结果，包括：
- **成功和失败的模式**：在哪些任务或场景下表现好/差？是否有明显的模式？
- **结果的统计显著性**：实验结果是否有统计显著性分析？结果是否可靠？
- **与基线比较的公平性**：与基线方法的比较是否公平？是否在相同条件下进行比较？
- **潜在的混淆因素**：是否存在潜在的混淆因素（如计算资源、模型版本差异、超参数设置等）？

**要求**：请引用论文中的具体实验数据、表格或图表来支撑你的分析。

### 1.4 技术严谨性
- **算法实现细节**：评估算法实现的细节是否充分？关键步骤是否有详细说明？
- **计算复杂度分析**：是否有计算复杂度的分析？是否合理？
- **可扩展性考虑**：是否考虑了方法的可扩展性？是否有相关分析？

**要求**：请引用论文中的具体分析或说明来支撑你的评估。

## 2. 新颖性（Novelty）

请从以下方面评估论文的新颖性：

### 2.1 创新水平
请深入理解论文的技术创新，包括：
- **核心算法或方法的新颖之处**：论文提出的核心算法或方法有哪些新颖之处？与现有方法有什么本质区别？
- **技术创新对领域的贡献程度**：这些技术创新对领域可能产生什么影响？

**要求**：请引用论文中的具体方法描述、算法或技术细节来支撑你的评估。

### 2.2 贡献意义
- **学术价值**：评估论文贡献的学术价值，是否推动了领域的发展？
- **实用价值**：评估论文贡献的实用价值，是否有实际应用前景？

**要求**：请基于论文内容本身进行分析，引用论文中的相关说明或实验结果。

### 2.3 与现有工作的区别
基于论文中提到的相关工作（Related Work）部分和创新点分析，详细分析：
- **独特贡献**：论文的独特贡献是什么？与现有工作相比有什么本质区别？
- **改进程度**：如果是改进工作，改进的程度如何？是突破性改进还是渐进式改进？

**注意**：如果论文中没有明确提到相关工作，请基于论文内容本身和创新点分析进行评估。

## 3. 清晰度（Clarity）

请从以下方面评估论文的清晰度：

### 3.1 写作质量
- **表达清晰度**：评估论文的表达是否清晰、准确？技术描述是否易于理解？
- **术语使用**：评估技术术语的定义和使用是否一致、准确？

**要求**：请引用论文中的具体例子来说明。

### 3.2 逻辑流程和组织
- **结构合理性**：评估论文的结构是否合理？章节组织是否清晰？
- **逻辑清晰度**：评估论文的逻辑是否清晰？论证过程是否严密？

**要求**：请引用论文中的具体章节来说明。

### 3.3 呈现清晰度
- **图表质量**：评估图表、表格的清晰度和可读性
- **公式表达**：评估数学公式的表达是否清晰、规范？

**要求**：如果可能，请引用论文中的具体图表或公式来说明。

### 3.4 可读性
- **数学公式和符号的一致性**：评估数学公式和符号的使用是否一致？
- **关键概念的解释**：评估关键概念的解释是否充分？是否易于理解？

**要求**：请引用论文中的具体例子来说明。

## 4. 完整性（Completeness）

请从以下方面评估论文的完整性：

### 4.1 内容完整性
- **必要组成部分**：评估论文是否涵盖了必要的组成部分（引言、方法、实验、结果、讨论等）？
- **信息充分性**：评估论文提供的信息是否充分？是否有重要信息缺失？

### 4.2 实验充分性
请评估实验是否充分验证了论文的贡献，包括：
- **消融研究的完整性**：是否有充分的消融研究？是否验证了各个组件的有效性？
- **不同设置下的实验验证**：是否在不同设置下进行了实验验证？
- **失败案例的分析**：是否分析了失败案例？是否讨论了方法的局限性？

**要求**：请引用论文中的具体实验或分析来说明。

### 4.3 讨论深度
- **结果分析**：评估论文对结果的分析是否深入？是否深入讨论了结果的含义？
- **局限性讨论**：评估论文对局限性的讨论是否充分？是否诚实面对方法的局限性？

**要求**：请引用论文中的具体讨论内容来说明。

### 4.4 缺失要素
请识别论文中缺失的重要信息，如：
- **实现细节**：是否缺少关键的实现细节？
- **超参数设置**：超参数设置的合理性是否充分讨论？
- **可复现性相关信息**：是否提供了足够的信息以便复现？
- **资源消耗的讨论**：是否讨论了计算资源、存储资源等的消耗？

**要求**：请明确指出缺失的信息，并说明为什么这些信息重要。

## 评估要求总结

1. **详细具体**：对每个维度提供详细、具体的分析，避免泛泛而谈
2. **引用支撑**：引用具体的章节、表格或图表来支撑你的评估
3. **深入分析**：深入分析实验结果，识别成功和失败的模式
4. **客观建设性**：保持客观、建设性的评估态度
5. **基于内容**：所有评估必须基于论文内容本身，不得编造

请为每个维度提供详细分析。

请使用中文回答。所有输出内容都必须是中文。"""
    else:
        prompt = f"""You are a senior academic review expert with rich experience in paper reviewing and deep academic background. Please deeply evaluate the following paper from multiple dimensions based solely on the paper content itself.

**Key Principles**:
1. **Based on paper content**: All evaluation must strictly be based on the provided paper information. Do not fabricate or speculate about content not mentioned in the paper.
2. **Cite specific locations**: If the paper information includes section numbers, figure/table numbers (e.g., §3.3.1, Table 3, Figure 2), please cite these specific locations in your evaluation.
3. **Evidence support**: All evaluation conclusions must be supported by specific evidence, citing specific content, data, or results from the paper.
4. **Objective and in-depth**: Maintain an objective, constructive evaluation attitude and deeply analyze all aspects of the paper.

Structured Paper Information:
{structured_info[:8000]}

Innovation Analysis:
{innovation_analysis[:3000]}

Please conduct detailed evaluation from the following dimensions. **Each dimension must provide in-depth, specific analysis, avoiding generalizations**:

## 1. Technical Quality

Please evaluate the paper's technical quality from the following aspects:

### 1.1 Method Rationality and Reliability
- **Theoretical foundation**: Is the theoretical foundation of the method design solid? Is there sufficient theoretical support?
- **Technical approach**: Evaluate the rationality of the technical approach. Is the method design logically clear with explicit steps?
- **Algorithm design**: Evaluate the rationality of algorithm design. Are there clear algorithm descriptions and pseudocode?
- **Implementation details**: Does the paper provide sufficient implementation details? Is it easy to reproduce?

**Requirement**: Please cite specific sections, formulas, or algorithm descriptions from the paper to support your evaluation.

### 1.2 Experimental Design Quality
- **Experimental setup**: Evaluate the rigor of experimental setup, including dataset selection, evaluation metrics, experimental environment, etc.
- **Control experiments**: Evaluate the reasonableness of control groups. Are comparisons with related methods fair?
- **Evaluation metrics**: Evaluate the appropriateness of evaluation metrics. Are they comprehensive and reasonable?
- **Experimental scale**: Evaluate the scale and sufficiency of experiments. Are they sufficient to validate the paper's contributions?

**Requirement**: Please cite specific experimental setups, dataset information, or experimental results from the paper to support your evaluation.

### 1.3 Result Credibility and Validity
Please deeply analyze experimental results, including:
- **Patterns of success and failure**: In which tasks or scenarios does it perform well/poorly? Are there obvious patterns?
- **Statistical significance of results**: Do experimental results have statistical significance analysis? Are the results reliable?
- **Fairness of baseline comparison**: Are comparisons with baseline methods fair? Are they compared under the same conditions?
- **Potential confounding factors**: Are there potential confounding factors (e.g., computational resources, model version differences, hyperparameter settings, etc.)?

**Requirement**: Please cite specific experimental data, tables, or figures from the paper to support your analysis.

### 1.4 Technical Rigor
- **Algorithm implementation details**: Evaluate whether algorithm implementation details are sufficient. Are key steps explained in detail?
- **Computational complexity analysis**: Is there computational complexity analysis? Is it reasonable?
- **Scalability considerations**: Are scalability considerations included? Is there relevant analysis?

**Requirement**: Please cite specific analysis or explanations from the paper to support your evaluation.

## 2. Novelty

Please evaluate the paper's novelty from the following aspects:

### 2.1 Innovation Level
Please deeply understand the paper's technical innovations, including:
- **Novel aspects of core algorithms or methods**: What are the novel aspects of the core algorithms or methods proposed in the paper? What are the essential differences from existing methods?
- **Contribution level of technical innovation to the field**: What impact might these technical innovations have on the field?

**Requirement**: Please cite specific method descriptions, algorithms, or technical details from the paper to support your evaluation.

### 2.2 Contribution Significance
- **Academic value**: Evaluate the academic value of the paper's contributions. Does it advance the field?
- **Practical value**: Evaluate the practical value of the paper's contributions. Are there practical application prospects?

**Requirement**: Please analyze based on the paper content itself, citing relevant explanations or experimental results from the paper.

### 2.3 Differences from Existing Work
Based on the related work section mentioned in the paper and innovation analysis, provide detailed analysis:
- **Unique contributions**: What are the paper's unique contributions? What are the essential differences compared to existing work?
- **Improvement degree**: If it's improvement work, what is the degree of improvement? Is it a breakthrough improvement or an incremental improvement?

**Note**: If the paper does not explicitly mention related work, please evaluate based on the paper content itself and innovation analysis.

## 3. Clarity

Please evaluate the paper's clarity from the following aspects:

### 3.1 Writing Quality
- **Expression clarity**: Evaluate whether the paper's expression is clear and accurate. Are technical descriptions easy to understand?
- **Terminology usage**: Evaluate whether the definition and usage of technical terms are consistent and accurate?

**Requirement**: Please cite specific examples from the paper to illustrate.

### 3.2 Logical Flow and Organization
- **Structure reasonableness**: Evaluate whether the paper's structure is reasonable. Is the chapter organization clear?
- **Logical clarity**: Evaluate whether the paper's logic is clear. Is the argumentation process rigorous?

**Requirement**: Please cite specific sections from the paper to illustrate.

### 3.3 Presentation Clarity
- **Figure/table quality**: Evaluate the clarity and readability of figures and tables.
- **Formula expression**: Evaluate whether mathematical formulas are expressed clearly and standardly?

**Requirement**: If possible, please cite specific figures or formulas from the paper to illustrate.

### 3.4 Readability
- **Consistency of mathematical formulas and symbols**: Evaluate whether the usage of mathematical formulas and symbols is consistent?
- **Explanation of key concepts**: Evaluate whether explanations of key concepts are sufficient. Are they easy to understand?

**Requirement**: Please cite specific examples from the paper to illustrate.

## 4. Completeness

Please evaluate the paper's completeness from the following aspects:

### 4.1 Content Completeness
- **Necessary components**: Evaluate whether the paper covers necessary components (introduction, method, experiments, results, discussion, etc.)?
- **Information sufficiency**: Evaluate whether the information provided in the paper is sufficient. Are there important missing information?

### 4.2 Experimental Sufficiency
Please evaluate whether experiments sufficiently validate the paper's contributions, including:
- **Completeness of ablation studies**: Are there sufficient ablation studies? Do they validate the effectiveness of each component?
- **Experimental validation under different settings**: Are experiments conducted under different settings?
- **Analysis of failure cases**: Are failure cases analyzed? Are method limitations discussed?

**Requirement**: Please cite specific experiments or analyses from the paper to illustrate.

### 4.3 Discussion Depth
- **Result analysis**: Evaluate whether the paper's analysis of results is in-depth. Does it deeply discuss the meaning of results?
- **Limitation discussion**: Evaluate whether the paper's discussion of limitations is sufficient. Does it honestly face the method's limitations?

**Requirement**: Please cite specific discussion content from the paper to illustrate.

### 4.4 Missing Elements
Please identify important missing information in the paper, such as:
- **Implementation details**: Are key implementation details missing?
- **Hyperparameter settings**: Is the rationale for hyperparameter settings sufficiently discussed?
- **Reproducibility-related information**: Is sufficient information provided for reproduction?
- **Discussion of resource consumption**: Is the consumption of computational resources, storage resources, etc. discussed?

**Requirement**: Please clearly identify missing information and explain why this information is important.

## Evaluation Requirements Summary

1. **Detailed and specific**: Provide detailed, specific analysis for each dimension, avoiding generalizations.
2. **Citation support**: Cite specific sections, tables, or figures to support your evaluation.
3. **In-depth analysis**: Deeply analyze experimental results, identifying patterns of success and failure.
4. **Objective and constructive**: Maintain an objective, constructive evaluation attitude.
5. **Based on content**: All evaluation must be based on the paper content itself, do not fabricate.

Please provide detailed analysis for each dimension.

Please provide your evaluation in English."""
    
    return prompt


def get_review_generation_prompt_v2(structured_info: str, evaluation: str, innovation_analysis: str, language: str = 'en') -> str:
    """
    评阅报告生成Prompt V2 - 生成高质量的评阅报告
    严格要求格式、内容和质量
    """
    if language == 'zh':
        prompt = f"""你是一位资深的学术评阅专家，具有丰富的论文评阅经验和深厚的学术背景。基于论文信息、评估和创新分析，生成一份全面、深入、高质量的评阅报告。

**重要原则**：
1. **基于提供的信息**：所有内容必须基于提供的论文信息、评估和创新分析，不得编造
2. **引用具体位置**：必须引用论文中的具体章节、图表、表格或数据来支撑你的观点
3. **客观建设性**：保持客观、建设性的评阅态度，既要指出问题，也要肯定优点
4. **深入具体**：避免泛泛而谈，提供深入、具体的分析和建议

论文结构化信息：
{structured_info[:8000]}

多维度评估：
{evaluation[:4000]}

创新点分析：
{innovation_analysis[:3000]}

请严格按照以下格式和要求生成评阅报告：

# 摘要（Summary）

请提供精炼准确的摘要（200-250字），必须包含：
1. **论文的核心贡献**（2-3句话）：清晰说明论文的主要贡献和创新点
2. **主要方法或技术路线**（1-2句话）：简要说明论文采用的主要方法或技术路线
3. **关键实验结果和数据**（2-3句话）：必须包含具体的性能指标、准确率、提升幅度等具体数值，引用论文中的具体数据

**要求**：
- 摘要必须基于论文内容，引用具体的实验数据
- 如果论文中有性能提升数据，必须包含（如"在XX数据集上达到XX%的准确率，相比基线方法提升了XX%"）
- 如果论文中有多个实验，选择最重要的2-3个结果进行总结

摘要应该简洁明了，让读者快速了解论文的核心价值和主要成果。

# 优点（Strengths）

请按2-4个维度组织优点，每个维度：
1. **使用明确的主题句作为开头**（如"创新的图搜索算法"、"有效的知识集成方法"、"严谨的实验设计"等）
2. **详细说明该优点的具体表现和意义**：
   - 该优点在论文中是如何体现的？
   - 为什么这是一个优点？
   - 这个优点对领域或应用有什么意义？
3. **引用具体位置**：如果论文信息中包含章节号、图表号（如§3.3.1、Figure 2、Table 3等），必须引用这些具体位置
4. **引用具体数据**：引用具体的实验数据或结果来支撑你的观点（如"在XX任务上达到XX%的性能"、"相比基线方法提升了XX%"）

**要求**：
- 每个优点应该独立成段，逻辑清晰，有说服力
- 必须基于论文内容，不得编造
- 必须引用具体的章节、图表或数据
- 避免使用"很好"、"不错"等模糊表述，使用具体的事实和数据

示例格式：
```
### [优点主题]

[详细说明该优点的具体表现，引用具体章节、图表或数据。说明为什么这是一个优点，以及对领域或应用的意义。]
```

# 缺点/关注点（Weaknesses / Concerns）

请从以下维度分析缺点和关注点（至少涵盖3-4个维度）：

1. **技术细节**：实现细节、计算复杂度、算法设计等方面的不足
2. **方法论**：实验设计、比较方法、评估指标等方面的局限性
3. **实验设计**：实验设置、基线比较、结果分析等方面的不足
4. **可复现性**：代码可用性、超参数设置、资源需求等方面的关注点
5. **讨论深度**：对结果的分析、局限性的讨论是否充分

每个缺点应该：
- **明确指出具体的问题**：问题是什么？在论文的哪个部分？
- **说明为什么这是一个问题**：这个问题的影响或风险是什么？
- **引用具体位置**：如果可能，引用具体的章节、表格或图表
- **保持客观和建设性**：指出问题是为了帮助改进，不是批评

**要求**：
- 必须基于论文内容本身进行分析，不得编造问题
- 如果论文中已经讨论了某些局限性，请引用并评价其讨论是否充分
- 如果某些信息缺失（如实现细节、超参数设置等），请明确指出并说明为什么这些信息重要

示例格式：
```
### [缺点主题]

[明确指出具体问题，引用具体章节或位置。说明为什么这是一个问题，以及可能的影响或风险。]
```

# 给作者的问题（Questions for Authors）

请提出4-6个建设性问题，覆盖以下方面：
1. **技术细节**：关于算法实现、机制设计的具体问题
2. **实验分析**：关于实验结果、比较方法的问题
3. **泛化性**：关于方法适用性、扩展性的问题
4. **设计选择**：关于关键设计决策的理由和影响
5. **未来工作**：关于方法的改进方向或未来应用

每个问题应该：
- **具体明确**：直接针对论文中的技术点或方法，避免过于宽泛
- **有助于澄清**：有助于澄清论文中的模糊之处或深化理解
- **避免重复**：不要重复在"缺点/关注点"中已经提到的问题
- **建设性**：问题应该有助于改进论文或深化研究

**要求**：
- 问题必须基于论文内容，针对论文中实际存在的技术点或方法
- 避免过于宽泛或与论文无关的问题
- 问题应该有助于作者改进论文或读者理解论文

# 评分（Score）

请为以下维度评分，并为每个评分提供详细说明（2-3句话）：

- **总体（Overall）**: [X]/10
  [说明：简要说明总体评分的理由，综合考虑论文的创新性、技术质量、实验验证等方面。必须基于论文内容本身进行评估。]

- **新颖性（Novelty）**: [X]/10
  [说明：评估论文的创新程度，与现有工作的区别。必须引用论文中的具体创新点来支撑评分。]

- **技术质量（Technical Quality）**: [X]/10
  [说明：评估方法的合理性、实验设计的严谨性、结果的可信度。必须引用论文中的具体技术细节或实验结果来支撑评分。]

- **清晰度（Clarity）**: [X]/10
  [说明：评估论文的写作质量、逻辑组织、表达清晰度。可以引用论文中的具体章节或表达来说明。]

- **置信度（Confidence）**: [X]/5
  [说明：评估你对评阅结论的置信程度，考虑实验验证的充分性、结果的可复现性、信息提供的完整性等。]

**评分要求**：
1. 评分必须客观、公正，基于论文内容本身
2. 每个评分必须有详细的说明，说明评分的理由
3. 评分说明必须引用论文中的具体内容、数据或结果来支撑
4. 避免给出极端分数（如10/10或1/10），除非有充分的理由

**重要要求总结**：
1. **严格基于论文内容**：所有内容必须基于提供的论文信息、评估和创新分析，不得编造
2. **引用具体位置**：必须引用论文中的具体章节、图表、表格或数据
3. **提供具体数据**：在摘要和优点中，必须包含具体的实验数据或性能指标
4. **深入具体**：避免泛泛而谈，提供深入、具体的分析和建议
5. **客观建设性**：保持客观、建设性的评阅态度

请严格按照上述格式和要求生成评阅报告。

请使用中文回答。所有输出内容都必须是中文。"""
    else:
        prompt = f"""You are a senior academic review expert with rich experience in paper reviewing and deep academic background. Based on the paper information, evaluation, and innovation analysis, generate a comprehensive, in-depth, high-quality review report.

**Key Principles**:
1. **Based on provided information**: All content must be based on the provided paper information, evaluation, and innovation analysis. Do not fabricate.
2. **Cite specific locations**: Must cite specific sections, figures, tables, or data from the paper to support your points.
3. **Objective and constructive**: Maintain an objective, constructive review attitude. Point out problems while also acknowledging strengths.
4. **In-depth and specific**: Avoid generalizations. Provide in-depth, specific analysis and suggestions.

Structured Paper Information:
{structured_info[:8000]}

Multi-dimensional Evaluation:
{evaluation[:4000]}

Innovation Analysis:
{innovation_analysis[:3000]}

Please strictly follow the following format and requirements to generate the review report:

# Summary

Please provide a concise and accurate summary (200-250 words) that must include:
1. **Core contributions of the paper** (2-3 sentences): Clearly state the main contributions and innovation points of the paper.
2. **Main method or technical approach** (1-2 sentences): Briefly describe the main method or technical approach adopted in the paper.
3. **Key experimental results and data** (2-3 sentences): Must include specific performance metrics, accuracy rates, improvement margins, and other specific values. Cite specific data from the paper.

**Requirements**:
- The summary must be based on paper content and cite specific experimental data.
- If the paper has performance improvement data, it must be included (e.g., "achieved XX% accuracy on XX dataset, improved by XX% compared to baseline methods").
- If the paper has multiple experiments, select the most important 2-3 results for summary.

The summary should be concise and clear, allowing readers to quickly understand the core value and main achievements of the paper.

# Strengths

Please organize strengths into 2-4 dimensions. For each dimension:
1. **Use a clear topic sentence as the opening** (e.g., "Innovative graph search algorithm", "Effective knowledge integration method", "Rigorous experimental design", etc.).
2. **Detail the specific manifestations and significance of this strength**:
   - How is this strength reflected in the paper?
   - Why is this a strength?
   - What is the significance of this strength to the field or application?
3. **Cite specific locations**: If the paper information includes section numbers, figure/table numbers (e.g., §3.3.1, Figure 2, Table 3), you must cite these specific locations.
4. **Cite specific data**: Cite specific experimental data or results to support your points (e.g., "achieved XX% performance on XX task", "improved by XX% compared to baseline methods").

**Requirements**:
- Each strength should be an independent paragraph with clear logic and persuasiveness.
- Must be based on paper content, do not fabricate.
- Must cite specific sections, figures, or data.
- Avoid vague expressions like "very good" or "not bad". Use specific facts and data.

Example format:
```
### [Strength Topic]

[Detail the specific manifestations of this strength, citing specific sections, figures, or data. Explain why this is a strength and its significance to the field or application.]
```

# Weaknesses / Concerns

Please analyze weaknesses and concerns from the following dimensions (at least 3-4 dimensions):

1. **Technical details**: Deficiencies in implementation details, computational complexity, algorithm design, etc.
2. **Methodology**: Limitations in experimental design, comparison methods, evaluation metrics, etc.
3. **Experimental design**: Deficiencies in experimental setup, baseline comparison, result analysis, etc.
4. **Reproducibility**: Concerns about code availability, hyperparameter settings, resource requirements, etc.
5. **Discussion depth**: Whether the analysis of results and discussion of limitations are sufficient.

Each weakness should:
- **Clearly identify the specific problem**: What is the problem? In which part of the paper?
- **Explain why this is a problem**: What is the impact or risk of this problem?
- **Cite specific locations**: If possible, cite specific sections, tables, or figures.
- **Maintain objectivity and constructiveness**: Pointing out problems is to help improve, not to criticize.

**Requirements**:
- Must analyze based on the paper content itself, do not fabricate problems.
- If the paper has already discussed certain limitations, please cite and evaluate whether the discussion is sufficient.
- If certain information is missing (e.g., implementation details, hyperparameter settings, etc.), please clearly identify and explain why this information is important.

Example format:
```
### [Weakness Topic]

[Clearly identify the specific problem, citing specific sections or locations. Explain why this is a problem and possible impacts or risks.]
```

# Questions for Authors

Please propose 4-6 constructive questions covering the following aspects:
1. **Technical details**: Specific questions about algorithm implementation and mechanism design.
2. **Experimental analysis**: Questions about experimental results and comparison methods.
3. **Generalizability**: Questions about method applicability and scalability.
4. **Design choices**: Questions about the rationale and impact of key design decisions.
5. **Future work**: Questions about method improvement directions or future applications.

Each question should:
- **Be specific and clear**: Directly target technical points or methods in the paper. Avoid being too broad.
- **Help clarify**: Help clarify ambiguities in the paper or deepen understanding.
- **Avoid repetition**: Do not repeat questions already mentioned in "Weaknesses / Concerns".
- **Be constructive**: Questions should help improve the paper or deepen research.

**Requirements**:
- Questions must be based on paper content and target actual technical points or methods in the paper.
- Avoid overly broad or irrelevant questions.
- Questions should help authors improve the paper or help readers understand the paper.

# Score

Please score the following dimensions and provide detailed explanations (2-3 sentences) for each score:

- **Overall**: [X]/10
  [Explanation: Briefly explain the rationale for the overall score, comprehensively considering the paper's innovation, technical quality, experimental validation, etc. Must evaluate based on the paper content itself.]

- **Novelty**: [X]/10
  [Explanation: Assess the innovation level of the paper and differences from existing work. Must cite specific innovation points from the paper to support the score.]

- **Technical Quality**: [X]/10
  [Explanation: Assess the rationality of methods, rigor of experimental design, and credibility of results. Must cite specific technical details or experimental results from the paper to support the score.]

- **Clarity**: [X]/10
  [Explanation: Assess the writing quality, logical organization, and expression clarity of the paper. Can cite specific sections or expressions from the paper to illustrate.]

- **Confidence**: [X]/5
  [Explanation: Assess your confidence level in the review conclusions, considering the sufficiency of experimental validation, reproducibility of results, completeness of information provided, etc.]

**Scoring Requirements**:
1. Scores must be objective and fair, based on the paper content itself.
2. Each score must have a detailed explanation stating the rationale for the score.
3. Score explanations must cite specific content, data, or results from the paper to support.
4. Avoid extreme scores (e.g., 10/10 or 1/10) unless there is sufficient justification.

**Summary of Key Requirements**:
1. **Strictly based on paper content**: All content must be based on the provided paper information, evaluation, and innovation analysis. Do not fabricate.
2. **Cite specific locations**: Must cite specific sections, figures, tables, or data from the paper.
3. **Provide specific data**: In the summary and strengths, must include specific experimental data or performance metrics.
4. **In-depth and specific**: Avoid generalizations. Provide in-depth, specific analysis and suggestions.
5. **Objective and constructive**: Maintain an objective, constructive review attitude.

Please strictly follow the above format and requirements to generate the review report.

Please provide your review report in English."""
    
    return prompt

