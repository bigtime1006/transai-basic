<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <span>{{ isRegister ? '注册新用户' : '欢迎回来' }}</span>
        </div>
      </template>
      <el-form :model="form" @submit.prevent="handleSubmit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" @keyup.enter.prevent="focusPassword"></el-input>
        </el-form-item>
        <el-form-item v-if="isRegister">
          <el-input v-model="form.email" placeholder="邮箱（可选）"></el-input>
        </el-form-item>
        <el-form-item>
          <el-input type="password" v-model="form.password" placeholder="密码" @keyup.enter="handleSubmit" ref="passwordField"></el-input>
        </el-form-item>
        <el-form-item v-if="isRegister">
          <el-input type="password" v-model="form.confirmPassword" placeholder="确认密码"></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" class="submit-btn" :loading="submitting" :disabled="submitting">{{ isRegister ? '注册' : '登录' }}</el-button>
        </el-form-item>
      </el-form>
      <div class="switch-mode">
        <el-link type="primary" @click="isRegister = !isRegister" :disabled="!allowRegistration && !isRegister">
          {{ isRegister ? '已有账户？去登录' : '没有账户？去注册' }}
        </el-link>
      </div>
    </el-card>
  </div>
</template>

<script>
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { defineComponent, ref, reactive } from 'vue';
import { useRouter } from 'vue-router';

export default defineComponent({
  name: 'Login',
  emits: ['login-success'],
  setup(_, { emit }) {
    const router = useRouter();
    const isRegister = ref(false);
    const allowRegistration = ref(true);
    const form = reactive({
      username: '',
      email: '',
      password: '',
      confirmPassword: ''
    });
    const submitting = ref(false);
    const passwordField = ref(null);

    const focusPassword = () => {
      if (passwordField.value) {
        passwordField.value.focus();
      }
    };

    const checkRegistrationStatus = () => {
      axios.get('/api/admin/settings/registration')
        .then(response => {
          allowRegistration.value = response.data.allow_registration;
        })
        .catch(() => {
          allowRegistration.value = true;
        });
    };

    const fetchUserInfo = (token) => {
      axios.get('/api/users/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(response => {
        const userData = response.data;
        emit('login-success', {
          username: userData.username,
          role: userData.role || 'user'
        });
        ElMessage.success('登录成功，正在跳转...');
        router.push('/');
      })
      .catch(error => {
        console.error("Failed to fetch user info:", error);
        emit('login-success', {
          username: form.username,
          role: 'user'
        });
        ElMessage.success('登录成功，正在跳转...');
        router.push('/');
      });
    };

    const handleLogin = () => {
      if (submitting.value) return;
      submitting.value = true;
      const formData = new URLSearchParams();
      formData.append('username', form.username);
      formData.append('password', form.password);

      axios.post('/api/auth/token', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': ''
        }
      })
      .then(response => {
        const token = response.data.access_token;
        localStorage.setItem('token', token);
        fetchUserInfo(token);
      })
      .catch(error => {
        console.error("Login failed:", error);
        if (error.response) {
          ElMessage.error(`登录失败: ${error.response.data.detail || error.response.status}`);
        } else if (error.request) {
          ElMessage.error('登录失败: 未收到服务器响应');
        } else {
          ElMessage.error(`登录失败: ${error.message}`);
        }
      })
      .finally(() => { submitting.value = false; });
    };

    const handleRegister = () => {
      if (submitting.value) return;
      if (!allowRegistration.value) {
        ElMessage.error('用户注册当前已关闭');
        return;
      }
      if (form.password !== form.confirmPassword) {
        ElMessage.error('两次输入的密码不一致');
        return;
      }
      submitting.value = true;
      const payload = {
        username: form.username,
        password: form.password,
        email: form.email || `${form.username}@example.com`
      };
      axios.post('/api/users/register', payload)
        .then(() => {
          ElMessage.success('注册成功，请登录');
          isRegister.value = false;
        })
        .catch(error => {
          ElMessage.error(error.response?.data?.detail || '注册失败');
        })
        .finally(() => { submitting.value = false; });
    };

    const handleSubmit = () => {
      if (isRegister.value) {
        handleRegister();
      } else {
        handleLogin();
      }
    };

    checkRegistrationStatus();

    return {
      isRegister,
      allowRegistration,
      form,
      handleSubmit,
      passwordField,
      focusPassword,
      submitting
    };
  }
});
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f6f7;
}
.login-card {
  width: 400px;
}
.submit-btn {
  width: 100%;
}
.switch-mode {
  text-align: center;
  margin-top: 10px;
}
.card-header{ font-weight:600; font-size:18px; }
@media (max-width: 480px){
  .login-card{ width: 92vw; }
}
</style>
