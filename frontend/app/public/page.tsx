/*
  FE-02 /public 页面实现
  50篇引擎/更新时间卡+引入选空间下拉+批量copy进度+已引入防重复
*/
import React, { useEffect, useState } from "react";
import { Box, Button, Chip, CircularProgress, Divider, Grid, Menu, MenuItem, Paper, Select, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Toolbar, Typography, Tooltip } from "@mui/material";
import { Add, Download, Error, Refresh, Search } from "@mui/icons-material";

const publicArticles = Array.from({ length: 50 }, (_, i) => ({
  id: `article-${i + 1}`,
  title: `AI技术前沿：第 ${i + 1} 期深度解析`,
  source: ["AI前沿库", "机器学习周报", "科技评论"][Math.floor(Math.random() * 3)],
  engine: ["main", "builtin", "coze", "dify"][Math.floor(Math.random() * 4)],
  publishedAt: `2026-09-${15 - Math.floor(Math.random() * 10)}`,
  imported: Math.random() > 0.7, // 70% 未导入, 30% 已导入
  importProgress: Math.floor(Math.random() * 101),
}));

export default function PublicPage() {
  const [articles, setArticles] = useState(publicArticles);
  const [selectedTargetSpace, setSelectedTargetSpace] = useState("请选择目标空间");
  const [targetSpaces, setTargetSpaces] = useState([
    "旅程测试 (builtin)",
    "AI研究库 (main)", 
    "学习笔记 (coze)"
  ]);
  const [importProgress, setImportProgress] = useState(0);
  const [isImporting, setIsImporting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [showImportModal, setShowImportModal] = useState(false);

  // 搜索过滤
  const filteredArticles = articles.filter(article =>
    article.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    article.source.toLowerCase().includes(searchQuery.toLowerCase()) ||
    article.engine.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 批量导入处理
  const handleBatchImport = async () => {
    if (!selectedTargetSpace || selectedTargetSpace === "请选择目标空间" || isImporting) return;
    
    setIsImporting(true);
    setImportProgress(0);
    
    // 模拟导入过程
    const importInterval = setInterval(() => {
      setImportProgress(prev => {
        const newProgress = Math.min(100, prev + Math.random() * 5);
        if (newProgress >= 100) {
          clearInterval(importInterval);
          setIsImporting(false);
          // 标记选中的文章为已导入
          setArticles(prevArticles => 
            prevArticles.map(article => 
              article.importProgress > 0 
                ? { ...article, imported: true, importProgress: 100 } 
                : article
            )
          );
        }
        return newProgress;
      });
    }, 100);
  };

  // 单篇导入
  const handleImportArticle = (articleId: string) => {
    // 模拟单篇导入
    setTimeout(() => {
      setArticles(prevArticles => 
        prevArticles.map(article => 
          article.id === articleId 
            ? { ...article, imported: true, importProgress: 100 } 
            : article
        )
      );
    }, 500 + Math.random() * 1000);
  };

  // 下拉选择目标空间
  const handleTargetSpaceChange = (event: React.ChangeEvent<{ value: unknown }>) => {
    setSelectedTargetSpace(event.target.value as string);
  };

  // 清除导入状态（演示）
  const handleClearImport = () => {
    setArticles(articles.map(article => ({
      ...article,
      imported: false,
      importProgress: 0
    })));
  };

  return (
    <Box sx={{ p: 2 }}>
      <Toolbar>
        <Typography variant="h6">公共库</Typography>
        <Box sx={{ flexGrow: 1 }}>
          <TextField
            label="搜索公共库文章..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="输入文章标题、来源或引擎进行搜索"
            sx={{ width: 300 }}
            InputProps={{
              startAdornment: (
                <Icon>search</Icon>
              )
            }}
          />
        </Box>
        <Button
          variant="contained"
          size="small"
          onClick={() => console.log("刷新公共库")}
        >
          <Icon>refresh</Icon> 刷新
        </Button>
        <Button
          variant="outlined"
          size="small"
          onClick={handleClearImport}
        >
          <Icon>delete</Icon> 清除导入
        </Button>
      </Toolbar>

      {/* 目标空间选择下拉框 */}
      <Box sx={{ mb: 2 }}>
        <FormControl sx={{ width: 300 }}>
          <InputLabel id="target-space-label">目标空间</InputLabel>
          <Select
            labelId="target-space-label"
            value={selectedTargetSpace}
            label="目标空间"
            onChange={handleTargetSpaceChange}
            sx={{ width: 300 }}
          >
            {targetSpaces.map((space) => (
              <MenuItem key={space} value={space}>
                {space}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button
          variant="contained"
          sx={{ mt: 1 }}
          disabled={!selectedTargetSpace || selectedTargetSpace === "请选择目标空间" || isImporting}
          onClick={handleBatchImport}
        >
          {isImporting ? "导入中..." : "批量导入到选中空间"}
        </Button>
      </Box>

      {/* 导入进度条 */}
      {isImporting && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ mb: 1 }}>
            导入进度: {importProgress}%
          </Typography>
          <LinearProgress value={importProgress} sx={{ width: 400 }} />
          <Typography variant="caption" sx={{ textAlign: "right" }}>
            {importProgress}% 完成
          </Typography>
        </Box>
      )}

      {/* 文章列表 */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="h5">文章列表 ({filteredArticles.length} 篇可用)</Typography>
        <Divider sx={{ my: 1 }} />
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>文章标题</TableCell>
                <TableCell>来源</TableCell>
                <TableCell>引擎</TableCell>
                <TableCell>发布时间</TableCell>
                <TableCell>状态</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredArticles.map((article) => (
                <TableRow key={article.id} sx={{ borderBottom: "1px solid #eee" }}>
                  <TableCell component="th" scope="row">
                    <Box sx={{ maxWidth: 200 }}>
                      <Typography variant="body1" noWrap>
                        {article.title}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={article.source}
                      size="small"
                      sx={{ bgcolor: "#e3f2fd", color: "#1565c0" }}
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={article.engine}
                      size="small"
                      sx={{ 
                        bgcolor: article.engine === "builtin" ? "#e3f2fd" : "#f3e5f5",
                        color: article.engine === "builtin" ? "#1565c0" : "#6a1b9a"
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {article.publishedAt}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    {article.imported ? (
                      <Chip
                        label="已导入"
                        size="small"
                        color="success"
                        sx={{ bgcolor: "#e8f5e9", color: "#2e7d32" }}
                      >
                        <Icon>check</Icon>
                      </Chip>
                    ) : (
                      <Chip
                        label="未导入"
                        size="small"
                        color="warning"
                        sx={{ bgcolor: "#fff3e0", color: "#ef6c00" }}
                      >
         
