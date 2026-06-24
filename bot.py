npm i axios
------ app folder terminal ---

------------------------------------------------------------- APPLICATION ----------------------------------------------


------------------------------ REGISTER -------------------------------------------------------------

eh import lang ni boss para sa Axios nga variable
import { useNavigate } from 'react-router-dom';
import Axios from 'axios';




sa mga input nga box boss ibutang lang pareha ani


<input type="text" name="username" onChange={(e) => setUsernameReg(e.target.value)} required/>
                <label>Username</label>





    const [UsernameReg, setUsernameReg] = useState('');
    const [EmailReg, setEmailReg] = useState('');
    const [PasswordReg, setPasswordReg] = useState('');
    const [QuizmakerReg, setQuizmakerReg] = useState();




    const handleSubmit = (e) => {
        e.preventDefault();
    };

    const Register = () => {
        Axios.post('http://localhost:5170/register', {
            username: UsernameReg,
            email: EmailReg,
            password: PasswordReg,
            quizmaker: QuizmakerReg
        }).then(() => {
            alert('sucess registration');
        });

    };


------------------------------------------ LOGIN ---------------------------------------------------------

 
import { useNavigate } from 'react-router-dom';
import Axios from 'axios';
 



const navigate = useNavigate(); // Access the navigate function for redirection
  const [EmailLog, setEmailLog] = useState('');
  const [PasswordLog, setPasswordLog] = useState('');
  const [QuizmakerLog, setQuizmakerLog] = useState(false);
  const [admin, setAdmin] = useState(false);
  const LoginFailed = "Wrong information"




 const handleLogin = () => {
    Axios.post('http://localhost:5170/login', {
      email: EmailLog,
      password: PasswordLog
    })
      .then((response) => {
        const { role } = response.data;
        alert('Success login');
        if (role === "admin") {
          navigate('/admin');
        } else if (role === "quizmaker") {
          navigate('/quizmaker');
        } else {
          navigate('/quiztaker');
        }
      })
        .catch((error) => {
        console.error(error);
        alert('Login failed');
       
      });
  };










------------------------------------------------------ SERVER--------------------------------------------------

npm i express mysql cors body-parser nodemon
---- server folder terminal ------


const express = require('express');
const bodyParser = require('body-parser');
const app = express();
const mysql = require('mysql');
const cors = require('cors');

const db = mysql.createPool({
    host:'localhost',
    user: 'root',
    password: '',
    database: 'ProjectWeb'
});

app.use(cors())
app.use(express.json())
app.use(bodyParser.urlencoded({extended: true}))

app.get('/', (req, res)=>{
    res.send("server running well");
});

-------------------------- REGISTER ------------------------

app.post('/register', (req, res) => {
    const username = req.body.username;
    const email = req.body.email;
    const password = req.body.password;
    const quizmaker = req.body.quizmaker;
 
    const sqlregister = "INSERT INTO users (username, email, password, quizmaker) VALUES (?,?,?,?)";
    db.query(sqlregister, [username, email, password, quizmaker], (err, result) => {
      if (err) {
        console.error(err);
        res.status(500).json({ message: "Registration failed." });
      } else {
        console.log("Registration successful.");
        res.status(200).json({ message: "Registration successful." });
      }
    });
  });
 
--------------------------------- LOGIN ------------------------------------

  let userid = '';

  app.post('/login', (req, res) => {
    const email = req.body.email;
    const password = req.body.password;
 
    const sqlQuery = "SELECT * FROM users WHERE email = ? AND password = ?";
    db.query(sqlQuery, [email, password], (err, results) => {
      if (err) {
        console.error(err);
        res.status(500).json({ message: "Internal server error" });
      } else if (results.length === 0) {
        res.status(401).json({ message: "Invalid credentials" });
      } else {
        const user = results[0];
        userid = user.userid; // Store the user ID
        if (user.admin === 1) {
          res.json({ role: "admin" });
        } else if (user.quizmaker === 1) {
          res.json({ role: "quizmaker" });
        } else {
          res.json({ role: "quiztaker" });
        }
      }
    });
  });


app.listen(5170, () =>{
    console.log("running on port 5170");
})
