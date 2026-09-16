/*
  FE-02 /engines 页面实现
  5引擎卡+状态点+未配置灰不可点+tooltip+切换确认模态
*/
import React, { useEffect, useState } from "react";
import { Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, Grid, IconButton, LinearProgress, Menu, MenuItem, Paper, Select, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Toolbar, Typography, Tooltip } from "@mui/material";
import { Add, Error, Info, Refresh, Settings, Warning } from "@mui/icons-material";

const engines = [
  { 
    key: "builtin", 
    name: "主平台", 
    displayName: "主平台 (LangBot)", 
    description: "内置引擎，基于 LangBot，无需额外配置", 
    status: "configured",  // configured / allowlisted / unavailable
    keyStatus: "configured",
    isDefault: true,
    requiresKey: false,
    minUpload: true,
    minRetrieve: true,
  },
  { 
    key: "main", 
    name: "RAGFlow", 
    displayName: "RAGFlow", 
    description: "主平台自建 RAGFlow 引擎", 
    status: "unavailable",   // 待 Key 配置
    keyStatus: "unavailable",
    isDefault: false,
    requiresKey: true,
    minUpload: true,
    minRetrieve: true,
  },
  { 
    key: "coze", 
    name: "Coze", 
    displayName: "Coze", 
    description: "Coze 智能体平台", 
    status: "unavailable",   // 待 Key 配置
    keyStatus: "unavailable",
    isDefault: false,
    requiresKey: true,
    minUpload: true,
    minRetrieve: true,
  },
  { 
    key: "dify", 
    name: "Dify", 
    displayName: "Dify", 
    description: "Dify LLM 应用开发平台", 
    status: "unavailable",   // 待 Key 配置
    keyStatus: "unavailable",
    isDefault: false,
    requiresKey: true,
    minUpload: true,
    minRetrieve: true,
  },
  { 
    key: "fastgpt", 
    name: "FastGPT", 
    displayName: "FastGPT", 
    description: "FastGPT 知识库问答系统", 
    status: "unavailable",   // 待 Key 配置
    keyStatus: "unavailable",
    isDefault: false,
    requiresKey: true,
    minUpload: true,
    minRetrieve: true,
  },
];

export default function EnginesPage() {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [engineToSwitch, setEngineToSwitch] = useState<string | null>(null);
  const [currentSpace, setCurrentSpace] = useState("请选择目标空间");
  const [availableSpaces, setAvailableSpaces] = useState([
    "旅程测试 (builtin)",
    "AI研究库 (main)", 
    "学习笔记 (coze)"
  ]);

  // 检查引擎状态
  const getEngineStatus = (status: string) => {
    switch (status) {
      case "configured": return "已配置";
      case "allowlisted": return "已加白名单";
      case "unavailable": return "未配置";
      default: return status;
    }
  };

  const getEngineStatusColor = (status: string) => {
    switch (status) {
      case "configured": return "success.main";
      case "allowlisted": return "warning.main";
      case "unavailable": return "error.main";
      default: return "text.secondary";
    }
  };

  const getKeyStatusColor = (keyStatus: string) => {
    switch (keyStatus) {
      case "configured": return "success.main";
      case "unavailable": return "error.main";
      default: return "text.secondary";
    }
  };

  const handleOpenConfirm = (engineKey: string) => {
    setEngineToSwitch(engineKey);
    setShowConfirmDialog(true);
  };

  const handleCloseConfirm = () => {
    setShowConfirmDialog(false);
    setEngineToSwitch(null);
  };

  const handleConfirmSwitch = () => {
    if (!engineToSwitch) return;
    
    // 实际应用中应调用 PATCH /engine 接口
    console.log(`切换引擎为: ${engineToSwitch}`);
    console.log(`目标空间: ${currentSpace}`);
    
    // 更新引擎状态（演示）
    setEngines(prevEngines => 
      prevEngines.map(engine => 
        engine.key === engineToSwitch 
          ? { ...engine, status: "configured", keyStatus: "configured" } 
          : engine
      )
    );
    
    setShowConfirmDialog(false);
    setEngineToSwitch(null);
  };

  const handleSpaceChange = (event: React.ChangeEvent<{ value: unknown }>) => {
    setCurrentSpace(event.target.value as string);
  };

  return (
    <Box sx={{ p: 2 }}>
      <Toolbar>
        <Typography variant="h6">引擎管理</Typography>
        <Box sx={{ flexGrow: 1 }}>
          <Button
            variant="outlined"
            size="small"
            onClick={() => console.log("刷新引擎状态")}
          >
            <Icon>refresh</Icon> 刷新
          </Button>
        </Box>
      </Toolbar>

      {/* 目标空间选择 */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          当前操作将影响选中的空间：
        </Typography>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 1 }}>
          <Chip
            label="目标空间"
            size="small"
            sx={{ bgcolor: "#e3f2fd", color: "#1565c0" }}
          />
          <Select
            labelId="target-space-label"
            value={currentSpace}
            label="目标空间"
            onChange={handleSpaceChange}
            sx={{ width: 300 }}
          >
            {availableSpaces.map((space) => (
              <MenuItem key={space} value={space}>
                {space}
              </MenuItem>
            ))}
          </Select>
        </Box>
      </Box>

      {/* 引擎列表 */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="h5">引擎列表 ({engines.length} 个引擎)</Typography>
        <Divider sx={{ my: 1 }} />
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>引擎名称</TableCell>
                <TableCell>描述</TableCell>
                <TableCell>状态</TableCell>
                <TableCell>Key状态</TableCell>
                <TableCell>功能</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {engines.map((engine) => (
                <TableRow key={engine.key} sx={{ borderBottom: "1px solid #eee" }}>
                  <TableCell component="th" scope="row">
                    <Box display="flex" alignItems="center" gap={1}>
                      <Avatar
                        sx={{ width: 32, height: 32 }}
                        bgcolor={engine.key === "builtin" ? "#1976d2" : "#6a1b9a"}
                        color="white"
                      >
                        {engine.displayName.charAt(0)}
                      </Avatar>
                      <Typography variant="body1" noWrap>
                        {engine.displayName}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {engine.description}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={getEngineStatus(engine.status)}
                      size="small"
                      color={getEngineStatusColor(engine.status) as "error" | "info" | "primary" | "secondary" | "success" | "warning"}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={getKeyStatus(engine.keyStatus)}
                      size="small"
                      color={getKeyStatusColor(engine.keyStatus) as "error" | "info" | "primary" | "secondary" | "success" | "warning"}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Box display="flex" gap={1}>
                      <Chip
                        label={engine.minUpload ? "上传" : ""}
                        size="small"
                        sx={{ 
                          bgcolor: engine.minUpload ? "#e3f2fd" : "#f5f5f5",
                          color: engine.minUpload ? "#1565c0" : "#666"
                        }}
                      />
                      <Chip
                        label={engine.minRetrieve ? "检索" : ""}
                        size="s
