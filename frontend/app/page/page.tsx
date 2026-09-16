/*
  FE-01 / 工作台 页面实现
  展示: 空间卡 + 快捷动作 + 公共库推荐位 + 空态 CTA
*/
import React from "react";
import { Card, Grid, Avatar, Box, Button, Typography, Typography } from "@mui/material";
import { Refresh, Error, Info, Menu } from "@mui/icons-material";

const spaces = [
  { id: "1", name: "旅程测试", docCount: 5, engine: "builtin", updatedAt: "2026-09-10", isPublic: false },
  { id: "2", name: "公众号文章", docCount: 12, engine: "main", updatedAt: "2026-09-12", isPublic: false },
  { id: "3", name: "学习笔记", docCount: 0, engine: "coze", updatedAt: "2026-08-20", isPublic: false },
];

export default function HomePage() {
  const [showSkeleton, setShowSkeleton] = React.useState(false);

  return (
    <div style={{ minHeight: "100vh", padding: "2rem" }}>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6" style={{ mb: 1 }}>
          <Icon>space</Icon>我的知识空间
        </Typography>
        <Typography variant="body2" color="text.secondary">
          在这里管理和查询您的知识库
        </Typography>
      </Box>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        {spaces.map((space) => (
          <Grid item xs={12} sm={6} md={4} key={space.id}>
            <Card sx={{ p: 1, height: "100%" }}>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h6" noWrap>
                    {space.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {space.docCount} 篇文章
                  </Typography>
                </Box>
                <Avatar
                  sx={{ width: 32, height: 32 }}
                  bgcolor="#1976d2"
                  color="white"
                >
                  {space.name.substring(0, 1)}
                </Avatar>
                <Grid
                  container
                  alignItems="center"
                  justifyContent="flex-end"
                >
                  <Typography
                    variant="body1"
                    color="text.secondary"
                    fontSize="12px"
                  >
                    {space.updatedAt}
                  </Typography>
                </Grid>
              </Box>
              <Box pt={1}>
                <Button
                  variant="contained"
                  size="small"
                  sx={{ width: "100%" }}
                >
                  {space.docCount > 0 ? "查看详情" : "加入知识库"}
                </Button>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 空态 CTA */}
      {spaces.length === 0 && (
        <Card sx={{ p: 3, textAlign: "center", background: "#fafafa" }}>
          <Typography variant="h6" mb={1}>
            <Icon>add_circle</Icon> 还没有知识空间
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={2}>
            您还没有创建任何知识空间。点击下方按钮创建您的第一个空间。
          </Typography>
          <Button
            variant="contained"
            sx={{ mt: 1, width: "max-content", mx: "auto" }}
            onClick={() => window.location.href="/onboarding"}
          >
            创建第一个知识空间
          </Button>
        </Card>
      )}
    </div>
  );
}
