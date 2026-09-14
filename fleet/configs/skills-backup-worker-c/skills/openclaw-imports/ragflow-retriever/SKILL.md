# RAGFlow Retriever

## Overview

This skill provides direct access to the RAGFlow knowledge base for retrieving information from a large document collection (1045+ document chunks). 

**⚠️ IMPORTANT: This skill has very long retrieval times (5-15 minutes) due to the large knowledge base size. Please be patient and wait for the complete response.**

## Configuration

This skill uses the following RAGFlow configuration from the project:

- **Base URL**: `http://36.134.158.50:10001`
- **Agent ID**: `93474e90275e11f1866455338bedff8b`
- **API Key**: `ragflow-hcyEsMcbBXQjQBdqGtBvY9HEoh3toR_-JoSLQMnM5MY`

## When to Use This Skill

Use this skill when the user asks for:
- Information about华人移民 (Chinese immigration)
- Historical research on 南太平洋地区 (South Pacific region)
- Academic research requiring knowledge base queries
- Document retrieval and literature review
- Topics related to 岛国华人华侨 (overseas Chinese in island nations)

## How to Use

When a user requests information that requires searching the RAGFlow knowledge base:

1. **Invoke the MCP tool**: Use the `ask_agent` tool from ragflow-agent-mcp
2. **Wait patiently**: The retrieval takes 5-15 minutes due to the large document collection (1045+ chunks)
3. **Process the response**: Extract the relevant content from the response
4. **Format the output**: Present the information clearly to the user

## Example Usage

When user asks about "近代华人移民与南太平洋地区的历史":

```
Use the ragflow-agent-mcp ask_agent tool to query the knowledge base.
The question is: 近代华人移民与南太平洋地区（澳大利亚、新西兰、斐济、巴布亚新几内亚等）的历史，包括移民背景、人口分布、经济活动和社会影响

⚠️ Note: This query will take approximately 10 minutes due to the large knowledge base.
Please wait for the complete response before providing the answer to the user.
```

## Performance Notes

- **Retrieval Time**: 5-15 minutes depending on query complexity
- **Knowledge Base Size**: 1045+ document chunks
- **Data Source**: "岛国华人华侨" dataset

## Troubleshooting

If the query returns empty results:
1. Check if RAGFlow service is accessible at `http://36.134.158.50:10001`
2. Verify API key is valid
3. Try simplifying the query
4. Wait longer - large knowledge bases take more time

## Integration

This skill works with:
- RAGFlow MCP server (already configured in opencode.json)
- The knowledge base containing "岛国华人华侨" documents
- Metaso and Exa MCP for supplementary searches (if needed)

---

**Skill Version**: 1.0  
**Last Updated**: 2026-04-01  
**Maintainer**: ragflow-project  
**Note**: Please always inform users about the long retrieval time before querying