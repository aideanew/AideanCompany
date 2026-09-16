/*
  FE-01 /chat 页面实现
  分组选择器 + 流式消息 + meta/delta/done/error 叠加 + abort 静默 + asking 守卫 + 空态引导 + 流中断提示 + 401 回落
*/
import React, { useEffect, useState, useRef } from "react";
import { Box, Button, CircularProgress, Chip, Divider, IconButton, Input, InputLabel, List, ListItem, ListItemAvatar, ListItemText, Menu, MenuItem, Paper, Select, Stack, TextField, Typography, Tooltip, Avatar, AvatarGroup } from "@mui/material";
import { Add, Close, Error, Info, Refresh, Send, Warning } from "@mui/icons-material";

const initialMessages = [
  {
    id: "1",
    type: "meta",
    content: {
      source: "AI前沿库",
      engine: "main",
      timestamp: new Date().toISOString()
    },
    isUser: false
  },
  {
    id: "2",
    type": "delta",
    content: "GPT-4 是一种",
    isUser: false
  },
  {
    id: "3",
    type: "delta",
    content: "大型语言模型",
    isUser: false
  },
  {
    id: "4",
    type: "done",
    content: "",
    isUser: false
  }
];

const initialQuestions = [
  "今天的天气怎么样？",
  "请解释一下量子计算的原理",
  "如何快速学习一门新的编程语言？",
  "推荐一些经典的科幻小说",
  "机器学习中的过拟合是什么意思？"
];

export default function ChatPage() {
  const [messages, setMessages] = useState(initialMessages);
  const [inputValue, setInputValue] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [group, setGroup] = useState("我的知识库"); // 我的知识库 / 公共库
  const [sources, setSources] = useState(["我的知识库", "公共库"]);
  const [error, setError] = useState(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [isStreamInterrupted, setIsStreamInterrupted] = useState(false);
  const [showErrorRetry, setShowErrorRetry] = useState(false);
  const [showGroupSelector, setShowGroupSelector] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // 发送消息
  const sendMessage = async () => {
    if (!inputValue.trim() || isAsking) return;

    const userMessage = {
      id: Date.now().toString(),
      type: "text",
      content: inputValue,
      isUser: true
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue("");
    setIsAsking(true);
    setError(null);
    setIsStreamInterrupted(false);
    setShowErrorRetry(false);

    // 创建 abort controller
    const controller = new AbortController();
    setAbortController(controller);

    try {
      // 模拟 AI 响应流
      const aiResponse = await simulateAIResponse(inputValue, controller.signal);
      
      if (!aiResponse.aborted) {
        // 添加 meta 消息（来源信息）
        const metaMessage = {
          id: Date.now().toString() + "-meta",
          type: "meta",
          content: {
            source: group === "我的知识库" ? "旅程测试空间" : "AI前沿库",
            engine: group === "我的知识库" ? "builtin" : "main",
            timestamp: new Date().toISOString()
          },
          isUser: false
        };
        
        setMessages(prev => [...prev, metaMessage]);
        
        // 添加 delta 消息（实际内容）
        const deltaMessage = {
          id: Date.now().toString() + "-delta",
          type: "delta",
          content: aiResponse.content,
          isUser: false
        };
        
        setMessages(prev => [...prev, deltaMessage]);
        
        // 添加 done 消息
        const doneMessage = {
          id: Date.now().toString() + "-done",
          type: "done",
          content: "",
          isUser: false
        };
        
        setMessages(prev => [...prev, doneMessage]);
        
        // 检查是否被中断
        if (aiResponse.interrupted) {
          setIsStreamInterrupted(true);
          setShowErrorRetry(true);
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setError(err.message || "未知错误");
        setShowErrorRetry(true);
      }
    } finally {
      setIsAsking(false);
      setAbortController(null);
    }
  };

  // 模拟 AI 响应（带超时和中断模拟）
  const simulateAIResponse = async (prompt: string, signal: AbortSignal): Promise<{
    content: string;
    aborted: boolean;
    interrupted: boolean;
  }> => {
    return new Promise((resolve) => {
      // 模拟网络延迟
      setTimeout(() => {
        if (signal.aborted) {
          resolve({ content: "", aborted: true, interrupted: false });
          return;
        }
        
        // 模拟 20% 概率的流中断
        const shouldInterrupt = Math.random() < 0.2;
        const content = shouldInterrupt 
          ? "这是一个被中断的回答，内容可能不完整..."
          : "这是一个完整的回答。基于您的问题和知识库中的信息，我可以告诉您...";
        
        resolve({ 
          content, 
          aborted: false, 
          interrupted: shouldInterrupt 
        });
      }, 1500 + Math.random() * 1000); // 1.5-2.5秒延迟
    });
  };

  // 中断生成
  const abortGeneration = () => {
    if (abortController) {
      abortController.abort();
      setIsAsking(false);
      setAbortController(null);
      setIsStreamInterrupted(true);
      setShowErrorRetry(true);
    }
  };

  // 重试
  const retry = () => {
    setError(null);
    setShowErrorRetry(false);
    // 重新发送最后一条用户消息
    const lastUserMsg = messages.slice().reverse().find(msg => msg.isUser);
    if (lastUserMsg) {
      setInputValue(lastUserMsg.content);
      sendMessage();
    }
  };

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // 自动滚动到底部
  useEffect(() => {
    const chatContainer = document.getElementById("chat-container");
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  }, [messages]);

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* 头部：分组选择器 + 状态 */}
      <Box sx={{ 
        display: "flex", 
        justifyContent: "space-between", 
        alignItems: "center", 
        p: 2, 
        borderBottom: 1, 
        borderColor: "grey.200",
        backgroundColor: "grey.50"
      }}>
        <Box display="flex" alignItems="center" gap={2}>
          <Avatar sx={{ bgcolor: "primary.main", color: "white" }}>
            {group.charAt(0)}
          </Avatar>
          <Typography variant="h6" component="h3">
            {group}
          </Typography>
          <IconButton 
            size="small"
            onClick={() => setShowGroupSelector(true)}
            sx={{ p: 1 }}
          >
            <Icon>arrow_drop_down</Icon>
          </IconButton>
        </Box>
        <Box display="flex" alignItems="center" gap={2}>
          {isAsking && (
            <Tooltip title="正在思考...">
              <CircularProgress size={20} color="error.main" thickness={2} />
            </Tooltip>
          )}
          {!isAsking && error && (
            <Tooltip title={error}>
              <Button
                variant="text"
                size="small"
                color="error"
                onClick={retry}
              >
                <Icon>refresh</Icon>
              </Button>
            </Tooltip>
          )}
          {isStreamInterrupted && (
            <Tooltip title="回答可能不完整">
              <Chip
                label="回答可能不完整"
                size="small"
                color="warning"
                sx={{ bgcolor: "#fff3e0", color: "#ef6c00" }}
              />
            </Tooltip>
          )}
        </Box>
      </Box>

      {/* 分组选择器弹出 */}
      {showGroupSelector && (
        <Box sx={{ 
          position: "absolute", 
          top: 56, 
          left: 0, 
          right: 0, 
          background: "white", 
          zIndex: 1000, 
          boxShadow: "0px 4px 6px rgba(0,0,0,0.1)",
          zIndex: 1000
        }}>
          <List sx={{ width: "100%", maxHeight: 200 }}>
            {sources.map((source) => (
              <ListItem
                key={source}
                button
                onClick={() => {
                  setGroup(source);
                  setShowGroupSelector(false);
                  // 清空输入框（切换分组时）
              
