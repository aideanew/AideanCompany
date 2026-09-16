/*
  FE-01 /spaces 页面实现
  分组：我的 / 公共库
  每行引擎角标
*/
import React from "react";
import { Card, Grid, Avatar, Box, Button, Typography, Chip, Stack } from "@mui/material";

const mySpaces = [
  { id: "1", name: "旅程测试", engine: "builtin", docCount: 5, updatedAt: "2026-09-10" },
  { id: "2", name: "学习笔记", engine: "coze", docCount: 0, updatedAt: "2026-08-20" },
];

const publicSpaces = [
  { id: "3", name: "AI前沿库", engine: "main", docCount: 50, updatedAt: "2026-09-12" },
];

const engineTags = {
  builtin: "内置",
  main: "RAGFlow",
  coze: "Coze",
  dify: "Dify",
  fastgpt: "FastGPT",
};

export default function SpacesPage() {
  return (
    <div style={{ minHeight: "100vh", padding: "2rem" }}>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6" component="h2">
          <Icon>space</Icon>我的知识空间
        </Typography>
        <Typography variant="body2" color="text.secondary">
          管理和查询您的知识空间
        </Typography>
      </Box>

      {/* 分组标签 */}
      <Stack direction="horizontal" sx={{ mb: 2, justifyContent: "flex-end" }}>
        <Chip label="我的" variant="outlined" color="primary" sx={{ mr: 1 }} />
        <Chip label="公共库" variant="outlined" color="secondary" />
      </Stack>

      {/* 我的空间 */}
      <Grid container sx={{ mb: 2 }} spacing={2}>
        {mySpaces.map((space) => (
          <Grid item xs={12} sm={6} md={4} key={space.id}>
            <Card sx={{ p: 1, height: "100%" }}>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h6" noWrap>
                    {space.name}
                  </Typography>
                  <Chip
                    label={engineTags[space.engine] || space.engine}
                    size="small"
                    sx={{ mt: 0.5 }}
                  />
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    {space.docCount} 篇
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    更新于 {space.updatedAt}
                  </Typography>
                </Box>
              </Box>
              <Box pt={1}>
                <Button
                  variant="contained"
                  size="small"
                  sx={{ width: "100%" }}
                >
                  管理
                </Button>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 公共库 */}
      <Grid container sx={{ mb: 2 }} spacing={2}>
        {publicSpaces.map((space) => (
          <Grid item xs={12} sm={6} md={4} key={space.id}>
            <Card sx={{ p: 1, height: "100%" }}>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h6" noWrap>
                    {space.name}
                  </Typography>
                  <Chip
                    label={engineTags[space.engine] || space.engine}
                    size="small"
                    sx={{ mt: 0.5 }}
                  />
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    {space.docCount} 篇
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    更新于 {space.updatedAt}
                  </Typography>
                </Box>
              </Box>
              <Box pt={1}>
                <Button
                  variant="contained"
                  size="small"
                  sx={{ width: "100%" }}
                >
                  引入
                </Button>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 空态 */}
      <Grid container sx={{ mt: 2 }}>
        <Grid item xs={12}>
          <Card sx={{ p: 3, textAlign: "center", background: "#fafafa" }}>
            <Typography variant="h6" mb={1}>
              <Icon>folder</Icon> 还没有空间
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={2}>
              您还没有创建任何空间。点击上方“创建第一个知识空间”按钮开始。
            </Typography>
          </Card>
        </Grid>
      </Grid>
    </div>
  );
}
