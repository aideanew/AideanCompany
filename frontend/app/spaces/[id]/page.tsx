/*
  FE-01 /spaces/[id] 页面实现
  文档行：标题/来源/状态+缓存新抓标注+三入口+设置抽屉+loading+⚡toast+20003 reasons换链+30003重试+1.5s/80次
*/
import React, { useEffect, useState, useRef } from "react";
import { Card, Grid, Box, Button, Typography, Chip, Stack, CircularProgress, Tooltip, Menu, MenuItem, List, ListItem, Divider } from "@mui/material";
import { Refresh, Warning, Info, Error } from "@mui/icons-material";

const initialDocs = [
  { 
    id: "1", 
    title: "GPT-4 的主要特性有哪些？", 
    source: "AI前沿库", 
    sourceUrl: "https://mp.weixin.qq.com/s/xxx", 
    status: "ready", 
    version: 1,
    hitCount: 3,
    isNew: false,
    isCached: true,
  },
  { 
    id: "2", 
    title: "如何使用 LangChain 构建 LLM 应用", 
    source: "机器学习日报", 
    sourceUrl: "https://mp.weixin.qq.com/s/yyy", 
    status: "pending", 
    version: 1,
    hitCount: 0,
    isNew: true,
    isCached: false,
  },
  { 
    id: "3", 
    title: "2026年AI安全发展趋势", 
    source: "技术评论", 
    sourceUrl: "https://mp.weixin.qq.com/s/zzz", 
    status: "failed", 
    version: 1,
    hitCount: 0,
    isNew: false,
    isCached: false,
    errorReason: ["内容低质量", "来源不可信"],
  },
];

export default function SpaceDetailPage() {
  const spaceId = "1"; // 简化处理，实际应从路由获取
  const [docs, setDocs] = useState(initialDocs);
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // 模拟轮询获取文档状态（1.5s/80次）
  useEffect(() => {
    if (pollRef.current) return;
    
    let count = 0;
    const maxAttempts = 80;
    
    const poll = () => {
      if (count >= maxAttempts) {
        clearInterval(pollRef.current);
        pollRef.current = null;
        return;
      }
      
      // 模拟状态更新
      setDocs(prevDocs => 
        prevDocs.map(doc => 
          doc.status === "pending" && Math.random() > 0.7
            ? { ...doc, status: Math.random() > 0.5 ? "ready" : "failed", hitCount: doc.hitCount + 1 }
            : doc
        )
      );
      
      count++;
      if (count >= maxAttempts) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
    
    pollRef.current = setInterval(poll, 1500);
    
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [spaceId]);

  // 显示缓存命中 toast
  useEffect(() => {
    if (toastMessage) {
      // 实际应用中应该有 toast 组件
      console.log(`[TOAST] ${toastMessage}`);
      setTimeout(() => setToastMessage(null), 3000);
    }
  }, [toastMessage]);

  const handleAddArticle = () => {
    // 跳转到添加文章面板
    console.log("添加文章面板打开");
  };

  const handleSubscribeSource = () => {
    // 跳转到订阅公众号
    console.log("订阅公众号面板打开");
  };

  const handleImportPublic = () => {
    // 跳转到公共库引入
    console.log("公共库引入面板打开");
  };

  const handleOpenSettings = () => {
    setShowSettings(true);
  };

  const handleCloseSettings = () => {
    setShowSettings(false);
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "pending": return "处理中";
      case "ready": return "就绪";
      case "failed": return "失败";
      default: return status;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending": return "warning.main";
      case "ready": return "success.main";
      case "failed": return "error.main";
      default: return "text.secondary";
    }
  };

  return (
    <div style={{ minHeight: "100vh", padding: "2rem" }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Box>
          <Typography variant="h5" component="h2">
            知识空间详情
          </Typography>
          <Typography variant="body2" color="text.secondary">
            空间 ID: {spaceId}
          </Typography>
        </Box>
        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            size="small"
            onClick={handleAddArticle}
          >
            <Icon>add</Icon> 添加文章
          </Button>
          <Button
            variant="outlined"
            size="small"
            onClick={handleSubscribeSource}
          >
            <Icon>rss_feed</Icon> 订阅公众号
          </Button>
          <Button
            variant="outlined"
            size="small"
            onClick={handleImportPublic}
          >
            <Icon>library_add</Icon> 引入公共库
          </Button>
          <Button
            variant="contained"
            size="small"
            onClick={handleOpenSettings}
          >
            <Icon>settings</Icon> 设置
          </Button>
        </Box>
      </Box>

      {/* 缓存命中 Toast（简化实现） */}
      {toastMessage && (
        <Box sx={{ position: "fixed", top: 20, right: 20, zIndex: 1000 }}>
          <Card sx={{ p: 2, background: "#fff3e0", color: "#ef6c00" }}>
            <Typography variant="body2">
              {toastMessage}
            </Typography>
          </Card>
        </Box>
      )}

      {/* 文档列表 */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="h6" component="h3">
          文档列表 ({docs.length} 篇)
        </Typography>
        <Divider sx={{ my: 1 }} />
        <Box sx={{ maxHeight: "60vh", overflowY: "auto" }}>
          {docs.map((doc) => (
            <Card key={doc.id} sx={{ mb: 1, position: "relative" }}>
              <Box display="flex" alignItems="center" justifyContent="space-between" p={1}>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="h6" noWrap>
                    {doc.title}
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1} sx={{ mt: 0.5 }}>
                    <Chip
                      label={getStatusLabel(doc.status)}
                      size="small"
                      color={getStatusColor(doc.status) as "error" | "info" | "primary" | "secondary" | "success" | "warning"}
                    />
                    {doc.isNew && (
                      <Chip label="新" size="small" color="info" sx={{ bgcolor: "#e3f2fd", color: "#1565c0" }} />
                    )}
                    {doc.isCached && (
                      <Chip label="缓存" size="small" color="success" sx={{ bgcolor: "#e8f5e9", color: "#2e7d32" }} />
                    )}
                    {doc.version > 1 && (
                      <Chip label={`v${doc.version}`} size="small" color="warning" sx={{ bgcolor: "#fff3e0", color: "#ef6c00" }} />
                    )}
                  </Box>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="caption" color="text.secondary">
                    {doc.source}
                  </Typography>
                  <Tooltip title="查看来源">
                    <Icon>link</Icon>
                  </Tooltip>
                </Box>
                <Box display="flex" alignItems="center" gap={1}>
                  {doc.isCached && (
                    <Tooltip title="点击查看缓存详情">
                      <Button
                        variant="text"
                        size="small"
                        color="info"
                        onClick={() => console.log("查看缓存详情")}
                      >
                        <Icon>remove_red_eye</Icon>
                      </Button>
                    </Tooltip>
                  )}
                  {doc.errorReason && doc.errorReason.length > 0 && (
                    <Tooltip title={doc.errorReason.join(", ")}>
                      <Button
                        variant="text"
                        size="small"
                        color="error"
                        onClick={() => console.log("查看失败原因")}
                      >
                        <Icon>error_outline</Icon>
              
