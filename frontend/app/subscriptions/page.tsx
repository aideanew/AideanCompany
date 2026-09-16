/*
  FE-02 /subscriptions 页面实现
  订阅列表 + 任务进度条 + 5s轮询GET/jobs/{id} + PARTIAL重试 N篇
*/
import React, { useEffect, useState } from "react";
import { Box, Button, CircularProgress, Chip, Table, TableBody, TableCell, TableContainer, TableFooter, TableHead, TableRow, Toolbar, Typography } from "@mui/material";
import { Refresh, Download, Error, Schedule } from "@mui/icons-material";

const subscriptionJobs = [
  { 
    id: "job-1", 
    title: "公众号文章爬取", 
    source: "知乎日报", 
    status: "running", 
    progress: 67,
    total: 50,
    current: 33,
    nextRunAt: "2026-09-15 02:00",
    isPartial: false,
    retryCount: 0,
  },
  { 
    id: "job-2", 
    title: "知乎专栏导入", 
    source: "B站视频", 
    status: "partially_completed", 
    progress: 34,
    total: 50,
    current: 17,
    nextRunAt: "2026-09-15 01:30",
    isPartial: true,
    retryCount: 1,
  },
  { 
    id: "job-3", 
    title: "微信公众号归档", 
    source: "微信公众号", 
    status: "queued", 
    progress: 0,
    total: 50,
    current: 0,
    nextRunAt: "2026-09-15 03:00",
    isPartial: false,
    retryCount: 0,
  },
];

const statusLabels = {
  queued: { label: "排队中", color: "secondary.main" },
  running: { label: "进行中", color: "primary.main" },
  partially_completed: { label: "部分完成", color: "warning.main" },
  completed: { label: "已完成", color: "success.main" },
  failed: { label: "失败", color: "error.main" },
};

const statusColors = {
  queued: "secondary.main",
  running: "primary.main",
  partially_completed: "warning.main",
  completed: "success.main",
  failed: "error.main",
};

export default function SubscriptionsPage() {
  const [jobs, setJobs] = useState(subscriptionJobs);
  const [pollInterval, setPollInterval] = useState<number | null>(null);
  const [isPolling, setIsPolling] = useState(true);
  const [showPartialRetry, setShowPartialRetry] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  // 5秒轮询
  useEffect(() => {
    if (!isPolling) return;

    const interval = setInterval(async () => {
      // 模拟从后端获取最新状态
      const newJobs = jobs.map(job => {
        // 模拟进度变化
        const progressChange = Math.random() * 5 - 2.5;
        const newProgress = Math.max(0, Math.min(100, job.progress + progressChange));
        
        // 模拟状态变化
        let newStatus = job.status;
        if (newProgress >= 100) {
          newStatus = "completed";
        } else if (newProgress > 0 && newStatus === "queued") {
          newStatus = "running";
        }

        return { ...job, progress: Math.round(newProgress), status: newStatus };
      });

      setJobs(newJobs);
    }, 5000);

    return () => clearInterval(interval);
  }, [isPolling, jobs]);

  // 处理部分完成重试
  const handlePartialRetry = (jobId: string) => {
    setShowPartialRetry(false);
    // 标记为重试中
    setJobs(jobs.map(job => 
      job.id === jobId ? { ...job, retryCount: (job.retryCount || 0) + 1, status: "running" } : job
    ));
    // 实际应用中会调用 POST /jobs/{id}/retry
    console.log(`重试任务 ${jobId}`);
  };

  // 下载/查看详情
  const handleViewDetail = (jobId: string) => {
    console.log(`查看任务详情: ${jobId}`);
  };

  return (
    <Box sx={{ p: 2 }}>
      <Toolbar>
        <Typography variant="h6">订阅任务</Typography>
        <Button
          variant="outlined"
          size="small"
          onClick={() => console.log("新建订阅")}
        >
          <Icon>add</Icon> 新建
        </Button>
      </Toolbar>

      <Box sx={{ mt: 2 }}>
        {jobs.length === 0 && (
          <Box sx={{ p: 2, textAlign: "center", color: "text.secondary" }}>
            暂无订阅任务
          </Box>
        )}

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>任务</TableCell>
                <TableCell>进度</TableCell>
                <TableCell>状态</TableCell>
                <TableCell>下次同步</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobs.map((job) => (
                <TableRow key={job.id} sx={{ borderBottom: "1px solid #eee" }}>
                  <TableCell component="th" scope="row">
                    <Box display="flex" alignItems="center" gap={1}>
                      <Chip
                        label={job.title}
                        size="small"
                        sx={{ width: "100px" }}
                      />
                      <Chip
                        label={job.source}
                        size="small"
                        sx={{ bgcolor: "#e3f2fd", color: "#1565c0" }}
                      />
                    </Box>
                  </Box>
                  <TableCell align="center">
                    <Box sx={{ width: 80 }}>
                      <CircularProgress
                        size={20}
                        value={job.progress}
                        color={statusColors[job.status as keyof typeof statusColors] || "secondary.main"}
                        sx={{ mx: 0.5 }}
                      />
                      <Typography variant="caption" sx={{ textAlign: "center" }}>
                        {job.progress}%
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={statusLabels[job.status as keyof typeof statusLabels]?.label || job.status}
                      size="small"
                      color={statusColors[job.status as keyof typeof statusColors] || "secondary.main"}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="caption">
                      {job.nextRunAt}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Box display="flex" gap={1}>
                      <Button
                        variant="text"
                        size="small"
                        sx={{ mr: 0.5 }}
                        onClick={() => handleViewDetail(job.id)}
                      >
                        <Icon>remove_red_eye</Icon> 详情
                      </Button>
                      {job.isPartial && job.retryCount > 0 && (
                        <Button
                          variant="text"
                          size="small"
                          color="warning"
                          onClick={() => handlePartialRetry(job.id)}
                        >
                          <Icon>autorenew</Icon> 重试 N 篇
                        </Button>
                      )}
                      {job.status === "failed" && (
                        <Button
                          variant="text"
                          size="small"
                          color="error"
                          onClick={() => console.log(`重新提交 ${job.id}`)}
                        >
                          <Icon>error</Icon> 重新提交
                        </Button>
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {/* PARTIAL 重试模态框 */}
        {showPartialRetry && (
          <Box sx={{ 
            position: "fixed", 
            top: 0, 
            left: 0, 
            right: 0, 
            bottom: 0, 
            background: "rgba(0,0,0,0.5)", 
            zIndex: 1000
          }}>
            <Box sx={{ 
              position: "absolute", 
              top: 50%, 
              left: 50%, 
              transform: "translate(-50%, -50%)", 
              background: "white", 
              width: 400, 
              p: 2, 
              borderRadius: 2,
              boxShadow: "0px 4px 6px rgba(0,0,0,0.1)"
         
